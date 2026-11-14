---
spec_id: 001-create-and-list-in-memory-tasks
shape: service-python
spec_hash: b14ec7789033
summary: In-memory POST /tasks and GET /tasks with title and optional due date validation
tasks:
  - id: t1
    title: Add in-memory tasks package with POST and GET /tasks
    files: [src/taskboard15_api/tasks/__init__.py, src/taskboard15_api/tasks/models.py, src/taskboard15_api/tasks/store.py, src/taskboard15_api/tasks/router.py, src/taskboard15_api/main.py, tests/test_task_store.py]
    covers: [AC-001.1, AC-001.2, AC-001.3, AC-001.4, AC-001.5, AC-001.6, AC-001.7, AC-001.8]
    parallel_safe: true
    depends_on: []
---

# Plan — 001 Create and list in-memory tasks

One task: the models, store and router are small and only meaningful together; a split would serialise anyway (router imports models and store) and leave an intermediate task whose acceptance checks cannot pass. Contract and signatures: [design.md](design.md).

## t1 — Add in-memory tasks package with POST and GET /tasks

**Files:** src/taskboard15_api/tasks/__init__.py, src/taskboard15_api/tasks/models.py, src/taskboard15_api/tasks/store.py, src/taskboard15_api/tasks/router.py, src/taskboard15_api/main.py, tests/test_task_store.py
**Covers:** AC-001.1, AC-001.2, AC-001.3, AC-001.4, AC-001.5, AC-001.6, AC-001.7, AC-001.8
**Goal:** Clients can create tasks (title, optional due date) and list them in creation order, held in a per-app in-memory `TaskStore`, with invalid input rejected by FastAPI's standard 422 body naming the field, exactly as in the design's contract.

**Implementation notes:**
- `models.py`: `TaskCreate` with `title: StrictStr = Field(min_length=1, max_length=200)` plus a field validator rejecting whitespace-only titles (raise `ValueError`, do not trim the stored value); `due_date: StrictStr | None = None` with a field validator that requires `^\d{4}-\d{2}-\d{2}$` and converts via `datetime.date.fromisoformat` (its `ValueError` becomes a 422 on `due_date`). Unknown fields ignored (Pydantic default).
- `models.py`: `Task` response model `id: str`, `title: str`, `due_date: datetime.date | None` (serialises to `"YYYY-MM-DD"` / `null`).
- `store.py`: `TaskStore` with `create(title, due_date) -> Task` (id `str(uuid.uuid4())`, append) and `list() -> list[Task]` (copy, creation order), both under a `threading.Lock`. No module-level store instance.
- `router.py`: `get_task_store(request: Request) -> TaskStore` returning `request.app.state.task_store`; `APIRouter` with `POST /tasks` (`status_code=201`, `response_model=Task`) and `GET /tasks` (`response_model=list[Task]`), sync handlers, store injected with `Depends(get_task_store)`.
- `__init__.py`: re-export `router` and `TaskStore` (the design's test seam imports `TaskStore` from `taskboard15_api.tasks`).
- `main.py`: `app.state.task_store = TaskStore()` right after the app is created, and `app.include_router(router)`; keep health, ready, ping and metrics untouched.
- Log task creation with structlog (`task_created`, `task_id`), never the title (user content).
- `tests/test_task_store.py`: unit tests for the store (order, unique ids, list returns a copy) and the validators' edge cases (exactly 200 chars accepted, 201 rejected, `"2024-02-29"` accepted, `"2026-12-01T00:00:00"` and integer due dates rejected), to keep the 80 % coverage gate.

**Done when:** the acceptance tests for AC-001.1 to AC-001.8 pass (in-process, with a fresh `TaskStore` per test as the design's test seam describes), `tests/test_task_store.py` passes, existing health/metrics tests still pass, and `devbox run quality` is green.
