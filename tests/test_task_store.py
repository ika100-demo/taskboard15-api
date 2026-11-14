"""Unit tests for the task store and request validators."""

from __future__ import annotations

import datetime

import psycopg
import pytest
from pydantic import ValidationError

from taskboard15_api.db import Database, DatabaseUnavailable
from taskboard15_api.tasks import TaskStore
from taskboard15_api.tasks.models import TaskCreate


@pytest.fixture()
def store(clean_db: str) -> TaskStore:
    return TaskStore(Database(clean_db))


def test_store_keeps_creation_order(store: TaskStore) -> None:
    for title in ("A", "B", "C"):
        store.create(title, None)
    assert [t.title for t in store.list()] == ["A", "B", "C"]


def test_store_ids_unique_for_same_title(store: TaskStore) -> None:
    a = store.create("same", None)
    b = store.create("same", datetime.date(2026, 12, 1))
    assert a.id and b.id and a.id != b.id
    assert [t.due_date for t in store.list()] == [None, datetime.date(2026, 12, 1)]


def test_ensure_schema_twice_is_noop(clean_db: str) -> None:
    store = TaskStore(Database(clean_db))
    store.ensure_schema()
    store.ensure_schema()
    TaskStore(Database(clean_db)).ensure_schema()
    with psycopg.connect(clean_db) as conn:
        assert conn.execute("SELECT count(*) FROM tasks").fetchone() == (0,)


def test_unreachable_database_raises() -> None:
    store = TaskStore(Database("postgresql://u@127.0.0.1:1/x"))
    with pytest.raises(DatabaseUnavailable):
        store.list()


def test_missing_url_raises() -> None:
    with pytest.raises(DatabaseUnavailable):
        Database(None).ping()
    with pytest.raises(DatabaseUnavailable):
        Database("").ping()


def test_title_length_bounds() -> None:
    assert TaskCreate(title="x" * 200).title == "x" * 200
    with pytest.raises(ValidationError):
        TaskCreate(title="x" * 201)


def test_title_whitespace_rejected_and_not_trimmed() -> None:
    with pytest.raises(ValidationError):
        TaskCreate(title="   ")
    assert TaskCreate(title=" a ").title == " a "


def test_title_nul_rejected() -> None:
    with pytest.raises(ValidationError):
        TaskCreate(title="a\x00b")


def test_due_date_leap_day_accepted() -> None:
    assert TaskCreate(title="t", due_date="2024-02-29").due_date == datetime.date(2024, 2, 29)


@pytest.mark.parametrize("bad", ["2026-12-01T00:00:00", "2026-02-30", "tomorrow", 20261201])
def test_due_date_rejected(bad: object) -> None:
    with pytest.raises(ValidationError):
        TaskCreate.model_validate({"title": "t", "due_date": bad})
