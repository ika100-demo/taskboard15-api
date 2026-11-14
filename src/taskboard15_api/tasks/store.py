"""Postgres-backed task store."""

from __future__ import annotations

import datetime
import threading
import uuid

from ..db import Database
from .models import Task

_SCHEMA_LOCK_KEY = 7316002

_CREATE_TABLE = """
CREATE TABLE IF NOT EXISTS tasks (
    seq      bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    id       uuid   NOT NULL UNIQUE,
    title    text   NOT NULL,
    due_date date   NULL
)
"""


class TaskStore:
    """Holds tasks in the `tasks` table, in creation order."""

    def __init__(self, db: Database) -> None:
        self._db = db
        self._schema_ready = False
        self._lock = threading.Lock()

    def ensure_schema(self) -> None:
        """Create the table if needed, serialised across instances; once per instance."""
        if self._schema_ready:
            return
        with self._lock:
            if self._schema_ready:
                return
            with self._db.connection() as conn:
                conn.execute("SELECT pg_advisory_xact_lock(%s)", (_SCHEMA_LOCK_KEY,))
                conn.execute(_CREATE_TABLE)
            self._schema_ready = True

    def create(self, title: str, due_date: datetime.date | None) -> Task:
        self.ensure_schema()
        task = Task(id=str(uuid.uuid4()), title=title, due_date=due_date)
        with self._db.connection() as conn:
            conn.execute(
                "INSERT INTO tasks (id, title, due_date) VALUES (%s, %s, %s)",
                (task.id, task.title, task.due_date),
            )
        return task

    def list(self) -> list[Task]:
        self.ensure_schema()
        with self._db.connection() as conn:
            rows = conn.execute("SELECT id, title, due_date FROM tasks ORDER BY seq").fetchall()
        return [Task(id=str(row[0]), title=row[1], due_date=row[2]) for row in rows]
