---
spec_id: 001-create-and-list-in-memory-tasks
title: Create and list in-memory tasks
status: draft
priority: P1
shape: service-python
---

# 001 — Create and list in-memory tasks

## Problem

The task API so far answers only health, readiness and ping; a caller cannot record a single task. Clients that want to track work (a board UI, a script) have nothing to talk to. This first feature lets a caller create tasks with a title and an optional due date and list them back, kept in the service's memory, so that clients can be built against a real contract before any storage exists.

## Stories

As an API client, I want to create a task with a title and, if I have one, a due date, so that the work is recorded.

As an API client, I want to list all tasks, so that I can show what has been recorded.

## Acceptance criteria

- **AC-001.1** Given a running service, when a client sends `POST /tasks` with JSON `{"title": "Write report", "due_date": "2026-12-01"}`, then the response is `201` with a JSON task holding a non-empty string `id`, `title` "Write report" and `due_date` "2026-12-01". (smoke)
- **AC-001.2** Given a running service, when a client sends `POST /tasks` with only `{"title": "Buy milk"}`, then the response is `201` and the task's `due_date` is `null`.
- **AC-001.3** Given a running service, when a client sends `POST /tasks` with `title` missing, not a string, empty, only whitespace, or longer than 200 characters, then the response is `422` with an error body naming the `title` field, and no task is created (a following `GET /tasks` does not contain it).
- **AC-001.4** Given a running service, when a client sends `POST /tasks` with a `due_date` that is not a valid calendar date in `YYYY-MM-DD` form (for example "2026-02-30", "01.12.2026" or "tomorrow"), then the response is `422` with an error body naming the `due_date` field, and no task is created.
- **AC-001.5** Given tasks were created in the order A, B, C, when a client sends `GET /tasks`, then the response is `200` with a JSON array of exactly those tasks in creation order (A first), each with `id`, `title` and `due_date` as returned on creation. (smoke)
- **AC-001.6** Given no task has been created since the service started, when a client sends `GET /tasks`, then the response is `200` with an empty JSON array.
- **AC-001.7** Given two tasks created with the same title, when they are listed, then both appear, each with a different `id`.
- **AC-001.8** Given tasks were created, when the service restarts, then `GET /tasks` returns an empty array (tasks live only in memory).

## Non-goals

- Persisting tasks across restarts or sharing them between service instances.
- Reading, updating, completing or deleting a single task.
- Filtering, sorting options, search or pagination of the list.
- Authentication, users or task ownership.
- Times of day or time zones on due dates.

## Assumptions

- **A1** Resource path is `/tasks`; fields are `id`, `title`, `due_date` (other option: `/api/v1/tasks`, camelCase `dueDate`; affects AC-001.1 to AC-001.7).
- **A2** Due date is a calendar date in ISO `YYYY-MM-DD`, no time part (other option: full ISO date-time; affects AC-001.1, AC-001.4).
- **A3** Due dates in the past are accepted (other option: reject with `422`; affects AC-001.1, AC-001.4).
- **A4** Title is 1 to 200 characters and must contain a non-whitespace character; it is stored as sent, not trimmed (other option: trim, or a different limit; affects AC-001.3).
- **A5** Invalid input answers `422` with the framework's standard validation error body (other option: `400` with a custom body; affects AC-001.3, AC-001.4).
- **A6** `id` is a server-generated opaque unique string; clients cannot set it (other option: sequential integers; affects AC-001.1, AC-001.7).
- **A7** The list is a bare JSON array in creation order, oldest first, with no upper bound on count (other option: an object wrapper `{"tasks": [...]}`, newest first; affects AC-001.5, AC-001.6).
- **A8** Duplicate titles are allowed (other option: reject with `409`; affects AC-001.7).

## Open questions

None.

## Changelog

- 2026-11-14 created
