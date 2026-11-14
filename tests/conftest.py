"""Shared pytest fixtures."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from taskboard15_api.main import app


@pytest.fixture()
def task_client() -> TestClient:
    """A TestClient with a fresh, empty task store (equivalent to a service restart)."""
    try:
        from taskboard15_api.tasks import TaskStore
    except ImportError:  # feature not built yet: tests then fail on the missing routes
        return TestClient(app)
    app.state.task_store = TaskStore()
    return TestClient(app)


@pytest.fixture()
def client() -> TestClient:
    """A TestClient for the FastAPI application."""
    return TestClient(app)
