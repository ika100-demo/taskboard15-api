---
spec_id: 002-store-tasks-in-postgres-instead-of
shape: service-python
spec_hash: 33514b7bae35
summary: Persist tasks in Postgres (psycopg 3, idempotent schema under an advisory lock), 503 when the database is down, DB-aware readiness
tasks:
  - id: t1
    title: Replace the in-memory store with a Postgres-backed one and a DB-aware readiness probe
    files: [src/taskboard15_api/db.py, src/taskboard15_api/tasks/store.py, src/taskboard15_api/tasks/models.py, src/taskboard15_api/tasks/__init__.py, src/taskboard15_api/main.py, tests/test_task_store.py, tests/test_health.py, docs/env-vars.md, pyproject.toml, uv.lock, devbox.json, devbox.lock]
    covers: [AC-002.1, AC-002.2, AC-002.3, AC-002.4, AC-002.5, AC-002.6, AC-002.7]
    parallel_safe: true
    depends_on: []
---

# Plan — 002 Store tasks in Postgres instead of memory

One task: the connection layer, the store and the app factory only make the acceptance tests pass together (every criterion needs all three), and a split would serialise anyway. No gitops task: the system plan already wires `DATABASE_URL` and 2 dev replicas for this component. Contract, schema and signatures: [design.md](design.md).

## t1 — Replace the in-memory store with a Postgres-backed one and a DB-aware readiness probe

**Files:** src/taskboard15_api/db.py, src/taskboard15_api/tasks/store.py, src/taskboard15_api/tasks/models.py, src/taskboard15_api/tasks/__init__.py, src/taskboard15_api/main.py, tests/test_task_store.py, tests/test_health.py, docs/env-vars.md, pyproject.toml, uv.lock, devbox.json, devbox.lock
**Covers:** AC-002.1, AC-002.2, AC-002.3, AC-002.4, AC-002.5, AC-002.6, AC-002.7
**Goal:** Tasks are stored in the Postgres database named by `DATABASE_URL`, survive restarts and are shared between instances, the schema is created safely by concurrently starting instances, and an unreachable database answers `503 {"detail": "database unavailable"}` on `/tasks` and `503 {"status": "not ready"}` on `/ready` (while `/health` stays `200`), recovering without a restart, exactly as the design's contract says.

**Implementation notes:**
- Dependencies: runtime `psycopg[binary]>=3.2`; dev `pytest-postgresql>=6`; devbox package `postgresql@16` (gives `pg_ctl`/`initdb` to the test fixtures locally and in CI). Change them through the devbox recipes / `uv` lock flow, never `pip`; commit `uv.lock` and `devbox.lock`.
- `db.py`: `DatabaseUnavailable` and `Database(url)` with the `connection()` context manager and `ping()` from the design: `connect_timeout=2`, `options="-c statement_timeout=3000"`, `application_name="taskboard15-api"`; map `psycopg.OperationalError` and `psycopg.InterfaceError` (and a missing/empty URL) to `DatabaseUnavailable`; log `database_unavailable` with the exception class name only, never the URL or message.
- `tasks/store.py`: `TaskStore(db)`; `ensure_schema()` runs `SELECT pg_advisory_xact_lock(7316002)` + the design's `CREATE TABLE IF NOT EXISTS tasks` in one transaction, then sets a per-instance flag under a `threading.Lock`; `create()` and `list()` call it first. `create()` inserts `(id, title, due_date)` with bound parameters in a transaction and returns the `Task`; `list()` selects `ORDER BY seq` and returns `id` as `str`.
- `tasks/models.py`: the title validator also rejects a title containing `"\x00"` (`ValueError`, so 422 on `title`); all other rules untouched.
- `tasks/__init__.py`: keep the re-exports `router`, `TaskStore`; update the docstring.
- `main.py`: `create_app(database_url: str | None = None)` building the app (middleware, optional OTel instrumentation, router, health, ping, metrics as today), with `app.state.db` and `app.state.task_store`; `None` reads `os.environ.get("DATABASE_URL")`, and an unset/empty value logs `database_url_missing` once. Logging and tracing configuration stay module-level, once. `app = create_app()` at module level (Dockerfile `CMD` unchanged).
- `main.py`: exception handler `DatabaseUnavailable` → `JSONResponse(status_code=503, content={"detail": "database unavailable"})`; `/ready` becomes `async def`, runs `ensure_schema()` + `ping()` via `asyncio.to_thread` under `asyncio.wait_for(timeout=1.0)` and answers `200 {"status": "ready"}` or `503 {"status": "not ready"}`; `/health` unchanged.
- `tests/test_task_store.py`: keep the validator unit tests, add the NUL-title case, replace the in-memory store tests with store tests against the `pg_url` fixture from `tests/conftest.py` (order, unique ids, `ensure_schema()` twice is a no-op, a never-reachable URL raises `DatabaseUnavailable`), to hold the 80 % coverage gate.
- `tests/test_health.py`: `test_ready_returns_ready` builds its client from `create_app(database_url=pg_url)`; add the case that the module app without `DATABASE_URL` answers `/ready` `503 {"status": "not ready"}` and `/health` `200`.
- `docs/env-vars.md`: a `Database` section with `DATABASE_URL` (libpq URI, unset = not ready; injected by the gitops entry's `postgres` resource).
- Test DSNs in tests carry no password (`postgresql://<user>@host:port/db`), so `devbox run secrets-scan` stays clean without a baseline refresh.

**Done when:** the acceptance tests for AC-002.1 to AC-002.7 and the unchanged 001 acceptance tests for AC-001.1 to AC-001.5 and AC-001.7 pass against the `pytest-postgresql` database from `tests/conftest.py`, `tests/test_task_store.py` and `tests/test_health.py` pass, and `devbox run ci` is green.
