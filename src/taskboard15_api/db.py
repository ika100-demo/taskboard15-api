"""Postgres connection factory with the service's timeouts and error mapping."""

from __future__ import annotations

import contextlib
from collections.abc import Iterator
from typing import Any

import psycopg
import structlog

log = structlog.get_logger()


class DatabaseUnavailable(Exception):  # noqa: N818
    """The database cannot be reached or did not answer in time."""


class Database:
    """Opens one connection per use; the URL is never logged."""

    def __init__(self, url: str | None) -> None:
        self._url = url

    @contextlib.contextmanager
    def connection(self) -> Iterator[psycopg.Connection[Any]]:
        """Yield a connection (transaction per block); map connection failures."""
        if not self._url:
            raise DatabaseUnavailable("DATABASE_URL is not set")
        try:
            with psycopg.connect(
                self._url,
                connect_timeout=2,
                options="-c statement_timeout=3000",
                application_name="taskboard15-api",
            ) as conn:
                yield conn
        except (psycopg.OperationalError, psycopg.InterfaceError) as err:
            log.warning("database_unavailable", error=type(err).__name__)
            raise DatabaseUnavailable("database unavailable") from err

    def ping(self) -> None:
        """Run `SELECT 1`; raise DatabaseUnavailable when it fails."""
        with self.connection() as conn:
            conn.execute("SELECT 1")
