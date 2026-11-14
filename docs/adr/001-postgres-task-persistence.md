# ADR-001: Postgres task persistence

**Status:** Proposed (2026-11-14)

## Context

Spec 002 moves tasks from the in-memory store to Postgres so they survive restarts and are shared by the 2 dev replicas. The system plan already wires the `postgres` resource (`DATABASE_URL`). The runtime image is slim, so no system libpq package is available.

## Decision

Tasks persist in Postgres via psycopg 3; the service creates its schema itself, idempotently, under an advisory lock

## Consequences

- psycopg 3 sync API (`psycopg[binary]`) keeps the existing sync handlers; the binary wheel bundles libpq.
- One connection per request (no pool) keeps timeouts exact and reconnects at once when the database returns.
- Concurrent replicas start safely because schema creation is idempotent and serialised by an advisory lock.
- Tests need a local Postgres (`pytest-postgresql`, devbox `postgresql@16`); no Docker.
- Details: `docs/specs/002-store-tasks-in-postgres-instead-of/design.md`.
