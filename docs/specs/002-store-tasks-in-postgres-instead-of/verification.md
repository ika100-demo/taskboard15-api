# Verification — 002 Store tasks in Postgres instead of memory

**Result:** pass
**Commit:** 0853013 · **Base:** dc6de11 · **Trace:** 7/7 criteria named by tests

| Criterion | Verdict | Tests | Implementation | Notes |
|---|---|---|---|---|
| AC-002.1 | met | `tests/test_tasks_postgres.py::test_tasks_survive_a_restart` | `src/taskboard15_api/tasks/store.py:44`, `src/taskboard15_api/tasks/store.py:54` | A, B, C (mixed due dates) created on one app; rows checked directly in Postgres; a second `create_app` on the same DB returns `200` and a list equal to the creation responses (id, title, due_date), in order. `ORDER BY seq` at `store.py:57`. |
| AC-002.2 | met | `tests/test_tasks_postgres.py::test_list_is_empty_on_empty_database` | `src/taskboard15_api/tasks/store.py:54` | `clean_db` drops the table; `200` and `[]` asserted. |
| AC-002.3 | met | `tests/test_tasks_postgres.py::test_task_created_on_one_instance_is_listed_on_another` | `src/taskboard15_api/main.py:34`, `src/taskboard15_api/tasks/store.py:44` | Two app objects on one DB; row checked in Postgres; the other instance lists exactly the created task (same id, title, due_date). |
| AC-002.4 | met | `tests/test_tasks_postgres.py::test_two_instances_starting_at_once_both_work` | `src/taskboard15_api/tasks/store.py:32` (advisory xact lock at `:40`), `src/taskboard15_api/main.py:59` | `/ready` called on both from two threads on a dropped table: both `200`, table exists, then `POST` `201` and `GET` `200` on each. |
| AC-002.5 | met | `tests/test_tasks_postgres.py::test_database_down_answers_503_and_stores_nothing`, `::test_unreachable_database_answers_503_within_5_seconds`, `::test_hanging_database_answers_503_within_5_seconds` | `src/taskboard15_api/db.py:26` (timeouts, error mapping at `:38`), `src/taskboard15_api/main.py:50` | GET and POST both `503` with body exactly `{"detail": "database unavailable"}`, each `< 5 s` (stopped DB, refused port, hung socket); after restart of Postgres `GET /tasks` is `200` without "ghost". |
| AC-002.6 | met | `tests/test_tasks_postgres.py::test_ready_follows_the_database_and_health_does_not`, `::test_ready_is_503_for_unreachable_database`, `tests/test_health.py::test_ready_returns_ready`, `::test_app_without_database_is_not_ready`, `tests/test_smoke_ready.py::test_ac_002_6_ready_answers_ready_smoke` | `src/taskboard15_api/main.py:64` (1 s `wait_for`, `503 {"status": "not ready"}` at `:69`), `src/taskboard15_api/main.py:55` | Same app object: `200` → DB stopped → `503 {"status": "not ready"}` with `/health` `200 {"status": "ok"}` → DB started → `200 {"status": "ready"}`, no restart. |
| AC-002.7 | met | `tests/test_tasks_postgres.py::test_create_then_list_last` | `src/taskboard15_api/tasks/router.py:27`, `src/taskboard15_api/tasks/store.py:44` | `201` with id (non-empty string), title "Write report", due_date "2026-12-01"; following `GET` `200`, last element equals the creation body (a prior task ensures "last" is meaningful). |

The unchanged 001 acceptance tests (AC-001.1 to AC-001.5, AC-001.7) in `tests/test_tasks.py` now run on the Postgres-backed `task_client`; the 001 tests for the superseded AC-001.6 and AC-001.8 were removed, and `docs/specs/001-create-and-list-in-memory-tasks/spec.md` marks both as superseded by AC-002.2 / AC-002.1.

## Non-goals

The spec lists no non-goals. No template-owned layout (none applies to this API) or unrelated behaviour was changed. ✔

## Deviations from the plan

- Files outside t1's `files`: `tests/conftest.py`, `tests/test_tasks.py`, `tests/test_tasks_postgres.py`, `tests/test_smoke_ready.py` (acceptance tests and fixtures, owned by the test phase per design "Test seam"); `docs/adr/001-postgres-task-persistence.md`, `docs/adr/README.md` (ADR referenced by the design); `docs/backlog.md` (generated index); `docs/specs/001-.../spec.md` (supersede markers for AC-001.6 / AC-001.8). Acceptable: all are process or test artefacts the design calls for.
- `tasks/models.py` rejects a title containing U+0000 with `422` on `title`, departing from the note "the 422 validation ... stay unchanged". Acceptable: documented in design.md (Postgres `text` cannot hold NUL; the alternative is a `500`), covered by `tests/test_task_store.py::test_title_nul_rejected`.
- t1 has `done: true`; no task lacks `done`.

## Contract

Matches the spec's contract and `design.md`: `503 {"detail": "database unavailable"}` on `/tasks` (`main.py:50`), `/ready` `200 {"status": "ready"}` / `503 {"status": "not ready"}` (`main.py:64`), `/health` independent of the DB (`main.py:55`), connect timeout 2 s / statement timeout 3 s (`db.py:30`), `DATABASE_URL` as the only new config (`main.py:36`, documented in `docs/env-vars.md`), schema with internal `seq` not exposed (`store.py:13`). ✔

## Smoke

SMOKE: tests/test_smoke_ready.py — `/ready` returning `200 {"status": "ready"}` was also the template behaviour before this feature, so the smoke check alone cannot distinguish a DB-wired deployment from the old one; it is meaningful only together with the in-process AC-002.6 tests (informational, does not affect the result).

## Mutation check (report only)

15 of 20 mutants of the changed code were caught by the acceptance tests (75 %; spec 152, report only).

Survived (a test that names the criterion would fail if it checked this):
- `src/taskboard15_api/db.py:33 2 → 3`
- `src/taskboard15_api/main.py:37 not dropped`
- `src/taskboard15_api/main.py:80 return value → None`
- `src/taskboard15_api/tasks/store.py:12 7316002 → 7316003`
- `src/taskboard15_api/tasks/store.py:42 True → False`
