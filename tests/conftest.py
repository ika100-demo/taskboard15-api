"""Shared pytest fixtures.

Spec 002: tests that touch tasks run against a real Postgres started by pytest-postgresql
(`pg_ctl` comes from the devbox package `postgresql`).
"""

from __future__ import annotations

import contextlib
import shutil
from collections.abc import Callable, Iterator
from typing import Any

import psycopg
import pytest
from fastapi.testclient import TestClient
from pytest_postgresql.factories import postgresql_proc

from taskboard15_api.main import app

postgresql_proc = postgresql_proc(executable=shutil.which("pg_ctl"))

DB_NAME = "postgres"


@pytest.fixture()
def pg_url(postgresql_proc: Any) -> Iterator[str]:
    """URL of the running test Postgres; it is running again after the test, whatever happened."""
    if not postgresql_proc.running():
        postgresql_proc.start()
    yield (
        f"postgresql://{postgresql_proc.user}@{postgresql_proc.host}:{postgresql_proc.port}"
        f"/{DB_NAME}"
    )
    if not postgresql_proc.running():
        postgresql_proc.start()


@pytest.fixture()
def clean_db(pg_url: str) -> str:
    """The test database with no `tasks` table (the service must create it)."""
    with psycopg.connect(pg_url, autocommit=True) as conn:
        conn.execute("DROP TABLE IF EXISTS tasks")
    return pg_url


@pytest.fixture()
def make_app(clean_db: str) -> Callable[[], TestClient]:
    """Factory for service instances (replicas or restarts) against the clean test database."""
    from taskboard15_api.main import create_app

    def _make() -> TestClient:
        return TestClient(create_app(database_url=clean_db))

    return _make


@pytest.fixture()
def task_client(clean_db: str) -> Iterator[TestClient]:
    """A TestClient on a service instance with an empty database."""
    from taskboard15_api.main import create_app

    with TestClient(create_app(database_url=clean_db)) as c:
        yield c


@pytest.fixture()
def db_down(postgresql_proc: Any) -> Callable[[], contextlib.AbstractContextManager[None]]:
    """Context manager that stops Postgres inside the block and starts it again afterwards."""

    @contextlib.contextmanager
    def _down() -> Iterator[None]:
        postgresql_proc.stop()
        try:
            yield
        finally:
            if not postgresql_proc.running():
                postgresql_proc.start()

    return _down


@pytest.fixture()
def client() -> TestClient:
    """A TestClient for the FastAPI application (module app, no database)."""
    return TestClient(app)
