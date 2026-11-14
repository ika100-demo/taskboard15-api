# Verification — 001 Create and list in-memory tasks

**Result:** pass
**Commit:** a9cedb9 · **Base:** 8724961 · **Trace:** 8/8 criteria named by tests (smoke: AC-001.1, AC-001.5)

| Criterion | Verdict | Tests | Implementation | Notes |
|---|---|---|---|---|
| AC-001.1 | met | `tests/test_tasks.py::test_create_task_with_due_date`, `tests/test_smoke_tasks.py::test_ac_001_1_create_task_smoke` | `src/taskboard15_api/tasks/router.py:27`, `src/taskboard15_api/tasks/store.py:20`, `src/taskboard15_api/tasks/models.py:33` | asserts 201, non-empty string `id`, `title` "Write report", `due_date` "2026-12-01" |
| AC-001.2 | met | `tests/test_tasks.py::test_create_task_without_due_date` | `src/taskboard15_api/tasks/models.py:17`, `src/taskboard15_api/tasks/models.py:30` | asserts 201 and `due_date` is `None` |
| AC-001.3 | met | `tests/test_tasks.py::test_invalid_title_is_422_and_not_stored`, `tests/test_tasks.py::test_title_of_200_characters_is_accepted` | `src/taskboard15_api/tasks/models.py:16`, `src/taskboard15_api/tasks/models.py:21-24` | covers missing, non-string (int, null, list), empty, whitespace-only, 201 chars; asserts 422, every `loc[-1] == "title"`, and `GET /tasks == []`; 200-char boundary accepted |
| AC-001.4 | met | `tests/test_tasks.py::test_invalid_due_date_is_422_and_not_stored` | `src/taskboard15_api/tasks/models.py:17`, `src/taskboard15_api/tasks/models.py:28-33` | covers "2026-02-30", "01.12.2026", "tomorrow", date-time, integer, boolean; asserts 422, `loc[-1] == "due_date"`, empty list afterwards |
| AC-001.5 | met | `tests/test_tasks.py::test_list_in_creation_order`, `tests/test_smoke_tasks.py::test_ac_001_5_list_tasks_answers_with_array`, `tests/test_smoke_tasks.py::test_ac_001_5_created_tasks_listed_in_order_smoke` | `src/taskboard15_api/tasks/router.py:36-39`, `src/taskboard15_api/tasks/store.py:22`, `src/taskboard15_api/tasks/store.py:25-27` | asserts 200 and list equals exactly the three POST bodies in order A, B, C |
| AC-001.6 | met | `tests/test_tasks.py::test_list_is_empty_initially` | `src/taskboard15_api/tasks/store.py:16`, `src/taskboard15_api/main.py:28` | asserts 200 and `[]` on a fresh store |
| AC-001.7 | met | `tests/test_tasks.py::test_same_title_tasks_get_different_ids` | `src/taskboard15_api/tasks/store.py:20` | asserts both listed and ids differ (in POST bodies and in list) |
| AC-001.8 | met | `tests/test_tasks.py::test_fresh_store_after_restart_is_empty` | `src/taskboard15_api/main.py:28`, `src/taskboard15_api/tasks/store.py:15-17` | restart simulated by a fresh `TaskStore`, the test seam the design names; the only state is the per-app store created at app startup, so a real restart behaves the same |

## Non-goals

No persistence, no single-task read/update/delete routes, no filtering/sorting/pagination parameters, no auth, no time-of-day handling (date-time strings are rejected). No template-owned files (health, ready, ping, metrics) changed; `main.py` only adds the store and router (`src/taskboard15_api/main.py:16-17`, `:28-29`). ✔

## Deviations from the plan

- `tests/conftest.py`, `tests/test_tasks.py`, `tests/test_smoke_tasks.py` are in no task's `files`; acceptable: they are the acceptance tests from the red commits (1d69181, 24a4e95), not coder changes.
- After the freeze the coder changed only `tests/test_tasks.py:103` (added `# noqa: I001`); acceptable, see below.
- All tasks (`t1`) are `done: true`.

## Contract

Matches `design.md`: `POST /tasks` 201 with `id`/`title`/`due_date`, FastAPI standard 422 with `loc` ending in the field, `GET /tasks` bare array oldest first, store on `app.state.task_store` via `get_task_store` (`src/taskboard15_api/tasks/router.py:19-21`), UUID4 ids, structlog `task_created` with `task_id` only (no title). ✔

## Suppressions in acceptance tests

| File | Line | Rule | False positive |
|---|---|---|---|
| `tests/test_tasks.py` | 103 | `noqa: I001` | yes, in effect: a pure import-order/grouping finding on the frozen function-local imports; fixing it would change the frozen test's code, behaviour is unaffected |

## Mutation check (report only)

13 of 13 mutants of the changed code were caught by the acceptance tests (100 %; spec 152, report only).
