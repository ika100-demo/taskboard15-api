"""Thread-safe in-memory task store."""

from __future__ import annotations

import datetime
import threading
import uuid

from .models import Task


class TaskStore:
    """Holds tasks in creation order; lost on restart."""

    def __init__(self) -> None:
        self._tasks: list[Task] = []
        self._lock = threading.Lock()

    def create(self, title: str, due_date: datetime.date | None) -> Task:
        task = Task(id=str(uuid.uuid4()), title=title, due_date=due_date)
        with self._lock:
            self._tasks.append(task)
        return task

    def list(self) -> list[Task]:
        with self._lock:
            return self._tasks.copy()
