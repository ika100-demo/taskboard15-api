"""HTTP routes for tasks."""

from __future__ import annotations

import datetime
from typing import Annotated, cast

import structlog
from fastapi import APIRouter, Depends, Request

from .models import Task, TaskCreate
from .store import TaskStore

log = structlog.get_logger()

router = APIRouter()


def get_task_store(request: Request) -> TaskStore:
    """Return the app's task store."""
    return cast(TaskStore, request.app.state.task_store)


StoreDep = Annotated[TaskStore, Depends(get_task_store)]


@router.post("/tasks", status_code=201, response_model=Task)
def create_task(body: TaskCreate, store: StoreDep) -> Task:
    """Create a task."""
    due = cast("datetime.date | None", body.due_date)
    task = store.create(body.title, due)
    log.info("task_created", task_id=task.id)
    return task


@router.get("/tasks", response_model=list[Task])
def list_tasks(store: StoreDep) -> list[Task]:
    """List tasks in creation order."""
    return store.list()
