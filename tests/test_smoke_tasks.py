"""Smoke tests for spec 001 (AC-001.1, AC-001.5): reach the service by base URL only."""

from __future__ import annotations

import uuid

import httpx
import pytest


@pytest.mark.smoke
def test_ac_001_5_list_tasks_answers_with_array(smoke_base_url: str) -> None:
    response = httpx.get(smoke_base_url + "/tasks", timeout=10)
    assert response.status_code == 200
    assert isinstance(response.json(), list)


@pytest.mark.smoke
@pytest.mark.writes
def test_ac_001_1_create_task_smoke(smoke_base_url: str) -> None:
    title = f"smoke-{uuid.uuid4()}"
    response = httpx.post(
        smoke_base_url + "/tasks", json={"title": title, "due_date": "2026-12-01"}, timeout=10
    )
    assert response.status_code == 201
    body = response.json()
    assert isinstance(body["id"], str)
    assert body["id"]
    assert body["title"] == title
    assert body["due_date"] == "2026-12-01"


@pytest.mark.smoke
@pytest.mark.writes
def test_ac_001_5_created_tasks_listed_in_order_smoke(smoke_base_url: str) -> None:
    titles = [f"smoke-{uuid.uuid4()}" for _ in range(2)]
    created = []
    for title in titles:
        response = httpx.post(smoke_base_url + "/tasks", json={"title": title}, timeout=10)
        assert response.status_code == 201
        created.append(response.json())
    listed = httpx.get(smoke_base_url + "/tasks", timeout=10)
    assert listed.status_code == 200
    items = listed.json()
    positions = [items.index(task) for task in created]
    assert positions == sorted(positions)
