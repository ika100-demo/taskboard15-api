"""Unit tests for the task store and request validators."""

from __future__ import annotations

import datetime

import pytest
from pydantic import ValidationError

from taskboard15_api.tasks import TaskStore
from taskboard15_api.tasks.models import TaskCreate


def test_store_keeps_creation_order() -> None:
    store = TaskStore()
    for title in ("A", "B", "C"):
        store.create(title, None)
    assert [t.title for t in store.list()] == ["A", "B", "C"]


def test_store_ids_unique_for_same_title() -> None:
    store = TaskStore()
    a = store.create("same", None)
    b = store.create("same", datetime.date(2026, 12, 1))
    assert a.id and b.id and a.id != b.id


def test_store_list_returns_copy() -> None:
    store = TaskStore()
    store.create("A", None)
    store.list().clear()
    assert len(store.list()) == 1


def test_title_length_bounds() -> None:
    assert TaskCreate(title="x" * 200).title == "x" * 200
    with pytest.raises(ValidationError):
        TaskCreate(title="x" * 201)


def test_title_whitespace_rejected_and_not_trimmed() -> None:
    with pytest.raises(ValidationError):
        TaskCreate(title="   ")
    assert TaskCreate(title=" a ").title == " a "


def test_due_date_leap_day_accepted() -> None:
    assert TaskCreate(title="t", due_date="2024-02-29").due_date == datetime.date(2024, 2, 29)


@pytest.mark.parametrize("bad", ["2026-12-01T00:00:00", "2026-02-30", "tomorrow", 20261201])
def test_due_date_rejected(bad: object) -> None:
    with pytest.raises(ValidationError):
        TaskCreate.model_validate({"title": "t", "due_date": bad})
