# Architecture decision records

| ADR | Decision |
|---|---|
| [001](001-postgres-task-persistence.md) | Tasks persist in Postgres via psycopg 3; the service creates its schema itself, idempotently, under an advisory lock |
