"""Acceptance tests for spec 001: create and list in-memory tasks."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


def test_create_task_with_due_date(task_client: TestClient) -> None:  # AC-001.1
    response = task_client.post("/tasks", json={"title": "Write report", "due_date": "2026-12-01"})
    assert response.status_code == 201
    body = response.json()
    assert isinstance(body["id"], str)
    assert body["id"]
    assert body["title"] == "Write report"
    assert body["due_date"] == "2026-12-01"


def test_create_task_without_due_date(task_client: TestClient) -> None:  # AC-001.2
    response = task_client.post("/tasks", json={"title": "Buy milk"})
    assert response.status_code == 201
    assert response.json()["due_date"] is None


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"title": 123},
        {"title": None},
        {"title": ["a"]},
        {"title": ""},
        {"title": "   \t "},
        {"title": "x" * 201},
    ],
)
def test_invalid_title_is_422_and_not_stored(  # AC-001.3
    task_client: TestClient, payload: dict[str, object]
) -> None:
    response = task_client.post("/tasks", json=payload)
    assert response.status_code == 422
    detail = response.json()["detail"]
    assert detail
    assert all(item["loc"][-1] == "title" for item in detail)
    listed = task_client.get("/tasks")
    assert listed.status_code == 200
    assert listed.json() == []


def test_title_of_200_characters_is_accepted(task_client: TestClient) -> None:  # AC-001.3
    response = task_client.post("/tasks", json={"title": "x" * 200})
    assert response.status_code == 201
    assert response.json()["title"] == "x" * 200


@pytest.mark.parametrize(
    "due_date",
    ["2026-02-30", "01.12.2026", "tomorrow", "2026-12-01T00:00:00", 20261201, True],
)
def test_invalid_due_date_is_422_and_not_stored(  # AC-001.4
    task_client: TestClient, due_date: object
) -> None:
    response = task_client.post("/tasks", json={"title": "Bad date", "due_date": due_date})
    assert response.status_code == 422
    detail = response.json()["detail"]
    assert detail
    assert all(item["loc"][-1] == "due_date" for item in detail)
    listed = task_client.get("/tasks")
    assert listed.status_code == 200
    assert listed.json() == []


def test_list_in_creation_order(task_client: TestClient) -> None:  # AC-001.5
    created = []
    for title, due in [("A", "2026-12-01"), ("B", None), ("C", "2025-01-31")]:
        response = task_client.post("/tasks", json={"title": title, "due_date": due})
        assert response.status_code == 201
        created.append(response.json())
    listed = task_client.get("/tasks")
    assert listed.status_code == 200
    assert listed.json() == created
    assert [t["title"] for t in listed.json()] == ["A", "B", "C"]


def test_list_is_empty_initially(task_client: TestClient) -> None:  # AC-001.6
    response = task_client.get("/tasks")
    assert response.status_code == 200
    assert response.json() == []


def test_same_title_tasks_get_different_ids(task_client: TestClient) -> None:  # AC-001.7
    r1 = task_client.post("/tasks", json={"title": "Same"})
    r2 = task_client.post("/tasks", json={"title": "Same"})
    assert (r1.status_code, r2.status_code) == (201, 201)
    first, second = r1.json(), r2.json()
    listed = task_client.get("/tasks").json()
    assert [t["title"] for t in listed] == ["Same", "Same"]
    assert first["id"] != second["id"]
    assert listed[0]["id"] != listed[1]["id"]


def test_fresh_store_after_restart_is_empty(task_client: TestClient) -> None:  # AC-001.8
    from taskboard15_api.tasks import TaskStore  # noqa: I001

    from taskboard15_api.main import app

    assert task_client.post("/tasks", json={"title": "Gone"}).status_code == 201
    app.state.task_store = TaskStore()  # simulated restart
    response = task_client.get("/tasks")
    assert response.status_code == 200
    assert response.json() == []
