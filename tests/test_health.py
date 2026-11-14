"""Smoke tests for health/ready/ping endpoints."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from taskboard15_api.main import create_app


def test_health_returns_ok(client: TestClient) -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_ready_returns_ready(task_client: TestClient) -> None:  # AC-002.6
    response = task_client.get("/ready")
    assert response.status_code == 200
    assert response.json() == {"status": "ready"}


def test_app_without_database_is_not_ready(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("DATABASE_URL", raising=False)
    ready = TestClient(create_app())
    response = ready.get("/ready")
    assert response.status_code == 503
    assert response.json() == {"status": "not ready"}
    assert ready.get("/health").status_code == 200


def test_ping_returns_project_name(client: TestClient) -> None:
    response = client.get("/ping")
    assert response.status_code == 200
    assert response.json() == {"pong": "taskboard15-api"}
