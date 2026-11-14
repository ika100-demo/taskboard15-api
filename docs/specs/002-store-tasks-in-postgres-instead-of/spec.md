---
spec_id: 002-store-tasks-in-postgres-instead-of
title: Store tasks in Postgres instead of memory
status: approved
priority: P1
shape: service-python
parent: ika100-demo/taskboard15-gitops:001-persistent-tasks-in-postgres-shown-and
---

# 002 — Store tasks in Postgres instead of memory

## Problem

The task API keeps tasks only in its memory: every restart, redeploy or new replica loses or splits them, so nobody can rely on the board. People also have no way to see or add tasks except by calling the API by hand, because the web UI has no features yet. This spec makes tasks durable in a Postgres database and gives people a page in the web UI where they see all tasks and create new ones.

## System context

Slice of the system plan `001-persistent-tasks-in-postgres-shown-and` in `ika100-demo/taskboard15-gitops` for `taskboard15-api` (service-python). The system criteria and the contract below are binding: every criterion of this spec implements one of them and names it: `(system AC-<NNN>.<n>)`.

### System criteria

- **AC-001.1** Given tasks A, B and C were created through `POST /tasks`, when the task API restarts or is redeployed, then `GET /tasks` returns `200` with exactly A, B and C in creation order, each with the same `id`, `title` and `due_date` as returned on creation.
- **AC-001.2** Given the task API runs with more than one replica, when a task is created through any of them, then every following `GET /tasks`, whichever replica answers, contains that task.
- **AC-001.3** Given the database cannot be reached, when a client sends `GET /tasks` or `POST /tasks`, then the response is `503` with a JSON error body, no task is created, and the API's readiness check reports not ready until the database is reachable again.
- **AC-001.6** Given the start page is open, when a person enters the title "Write report" and the due date 2026-12-01 and submits the form, then the new task appears at the end of the list without the person reloading the page, the form is cleared, and the task is still listed after a reload of the page and in `GET /tasks`.

### Contract

Caller: `taskboard15-web` (server side), at `API_URL` (`http://taskboard15-api` in the cluster). Callee:
`taskboard15-api`. JSON, UTF-8, no authentication (system A10, dev only).

### `GET /tasks`

- `200`: a bare JSON array of tasks, creation order, oldest first, no upper bound, no pagination.
- `503`: database unreachable, body `{"detail": "database unavailable"}`.

### `POST /tasks`

Request body:

| Field | Type | Rules |
|---|---|---|
| `title` | string, required | 1 to 200 characters (Unicode code points), at least one non-whitespace character; stored as sent, not trimmed |
| `due_date` | string or `null`, optional | calendar date `YYYY-MM-DD`; absent or `null` means no due date; past dates accepted |

Responses:

- `201`: the created task.
- `422`: invalid input, FastAPI's standard body `{"detail": [{"loc": ["body", "<field>"], "msg": "...", "type": "..."}]}`;
  the field is `loc[1]` (`title` or `due_date`). No task is created.
- `503`: database unreachable, body `{"detail": "database unavailable"}`. No task is created.

### Task

| Field | Type | Notes |
|---|---|---|
| `id` | string | server-generated, opaque, unique, never reused; clients cannot set it |
| `title` | string | as sent |
| `due_date` | string `YYYY-MM-DD` or `null` | |

### Probes (cluster only)

- `GET /ready`: `200 {"status": "ready"}` when the database answers; `503 {"status": "not ready"}` otherwise.
- `GET /health`: `200` while the process runs, independent of the database.

The web UI's `/api/ready` and `/api/health` do not call the task API.

No events.

### Errors

- Error bodies are JSON with a `detail` field: a string for `503`, FastAPI's list for `422`.
- The web UI treats `422` naming `title` as a field error at the title field (its messages, see its criteria), and any
  other `422` as a failed save.
- Any response the contract does not list for a call (other `4xx`, `5xx`, a non-JSON body, a body not matching the
  shapes above), a connection error and a timeout count as "the API answers with an error": on `GET /tasks` the page
  shows "Tasks could not be loaded. Try again later.", on `POST /tasks` it shows "Task could not be saved. Try again."
  and keeps the form values. The page itself never answers with an error page for this.
- The web UI logs each such failure with the status or error kind, never the task title.

### Timeouts

- Web to API, `GET /tasks`: 5 s total, no retry; on timeout the load message is shown.
- Web to API, `POST /tasks`: 5 s total, no retry (a retry could create the task twice); on timeout the save message is
  shown, and a later reload shows whether the task was stored.
- API to Postgres: connect timeout 2 s, statement timeout 3 s; on either, the request answers `503` within 5 s.
- `/ready` checks the database with a 1 s timeout, so a down database takes every replica out of rotation; the
  Service then refuses connections, which the web UI handles as unreachable. The API reconnects by itself when the
  database is back, without a restart.

### Provided by the system

The gitops part of this plan wires these for this repo; rely on them, do not ask for them again:

- resource `postgres`: env `DATABASE_URL`, `PGHOST`, `PGPORT`, `PGDATABASE`, `PGUSER`, `PGPASSWORD`
- replicas `2` in `dev`

### Notes for this repo

Connection from DATABASE_URL (PG* are set as well), injected by the gitops entry; no other config.
Schema creation must be idempotent and safe when two replicas start at once (dev runs 2).
Creation order is kept by an internal column (sequence or created_at); it is not exposed (system A1).
The 422 validation and the existing criteria AC-001.1 to AC-001.5 and AC-001.7 stay unchanged.

## Stories

<!-- As a <persona>, I want <goal>, so that <benefit>. -->

## Acceptance criteria

- **AC-002.1** Given tasks A, B and C were created through `POST /tasks`, when the service restarts against the same database, then `GET /tasks` returns `200` with exactly A, B and C in creation order, each with the same `id`, `title` and `due_date` as returned on creation (system AC-001.1) (replaces AC-001.8)
- **AC-002.2** Given an empty database, when a client sends `GET /tasks`, then the response is `200` with an empty JSON array (system AC-001.1) (replaces AC-001.6)
- **AC-002.3** Given two service instances use the same database, when a task is created through `POST /tasks` on one, then `GET /tasks` on the other contains it with the same `id`, `title` and `due_date` (system AC-001.2)
- **AC-002.4** Given two service instances start at the same time against an empty database, when both have reported ready, then `POST /tasks` and `GET /tasks` succeed on each of them (system AC-001.2)
- **AC-002.5** Given the database cannot be reached, when a client sends `GET /tasks` or `POST /tasks`, then the response is `503` with the JSON body `{"detail": "database unavailable"}` within 5 seconds, and once the database is back `GET /tasks` does not contain the task that was posted (system AC-001.3)
- **AC-002.6** Given the database cannot be reached, when `GET /ready` is called, then it answers `503` with `{"status": "not ready"}` while `GET /health` still answers `200`; when the database is reachable again, `GET /ready` answers `200` with `{"status": "ready"}` without a restart (system AC-001.3)
- **AC-002.7** Given the database is reachable, when a client sends `POST /tasks` with `{"title": "Write report", "due_date": "2026-12-01"}`, then the response is `201` with the task and the following `GET /tasks` lists it last (system AC-001.6)

## Non-goals

## Assumptions

<!-- Spec 149: decisions taken by default, approved with the spec. One bullet each: - **A1** <the decision> (other option: <…>; affects AC-…). A revised one is struck through (~~…~~), never deleted. -->

## Open questions

<!-- Only what may not be decided by default (spec 149): security or access, money, destroying or migrating data, or a request too ambiguous to build. Approval is refused while any is open. Strike answered ones (~~…~~) and fold the answer into the criteria. -->

## Changelog

- 2026-11-14 created from the system plan, with its criteria (spec 147)
- 2026-11-14 approved
