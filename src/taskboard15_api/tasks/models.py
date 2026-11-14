"""Request and response models for tasks."""

from __future__ import annotations

import datetime
import re

from pydantic import BaseModel, Field, StrictStr, field_validator

_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


class TaskCreate(BaseModel):
    """Body of `POST /tasks`."""

    title: StrictStr = Field(min_length=1, max_length=200)
    due_date: StrictStr | None = None

    @field_validator("title")
    @classmethod
    def _title_not_blank(cls, value: str) -> str:
        if value.strip() == "":
            raise ValueError("title must contain a non-whitespace character")
        return value

    @field_validator("due_date", mode="after")
    @classmethod
    def _due_date_valid(cls, value: str | None) -> datetime.date | None:
        if value is None:
            return None
        if not _DATE_RE.match(value):
            raise ValueError("due_date must be in YYYY-MM-DD form")
        return datetime.date.fromisoformat(value)


class Task(BaseModel):
    """A task as returned by the API."""

    id: str
    title: str
    due_date: datetime.date | None
