"""Acceptance tests for spec 002: tasks live in Postgres (real Postgres via pytest-postgresql)."""

from __future__ import annotations

import contextlib
import socket
import threading
import time
from collections.abc import Callable, Iterator

import psycopg
import pytest
from fastapi.testclient import TestClient

DbDown = Callable[[], contextlib.AbstractContextManager[None]]
MakeApp = Callable[[], TestClient]

UNAVAILABLE = {"detail": "database unavailable"}


def _db_titles(url: str) -> list[str]:
    """Titles read straight from the `tasks` table, bypassing the service."""
    with psycopg.connect(url, autocommit=True) as conn:
        return sorted(row[0] for row in conn.execute("SELECT title FROM tasks").fetchall())


@pytest.fixture()
def hanging_db_url() -> Iterator[str]:
    """URL of a local socket that accepts connections but never answers (a hung database)."""
    server = socket.socket()
    server.bind(("127.0.0.1", 0))
    server.listen(16)
    port = server.getsockname()[1]
    accepted: list[socket.socket] = []
    stop = threading.Event()

    def accept() -> None:
        server.settimeout(0.2)
        while not stop.is_set():
            try:
                accepted.append(server.accept()[0])
            except OSError:
                continue

    thread = threading.Thread(target=accept, daemon=True)
    thread.start()
    try:
        yield f"postgresql://u@127.0.0.1:{port}/x"
    finally:
        stop.set()
        thread.join(timeout=5)
        for conn in accepted:
            conn.close()
        server.close()


def test_tasks_survive_a_restart(make_app: MakeApp, clean_db: str) -> None:  # AC-002.1
    first = make_app()
    created = []
    for title, due in [("A", "2026-12-01"), ("B", None), ("C", "2025-01-31")]:
        response = first.post("/tasks", json={"title": title, "due_date": due})
        assert response.status_code == 201
        created.append(response.json())
    assert _db_titles(clean_db) == ["A", "B", "C"]  # the rows are in Postgres itself
    restarted = make_app()  # a second app object = the service restarted on the same database
    listed = restarted.get("/tasks")
    assert listed.status_code == 200
    assert listed.json() == created
    assert [t["title"] for t in listed.json()] == ["A", "B", "C"]


def test_list_is_empty_on_empty_database(task_client: TestClient) -> None:  # AC-002.2
    response = task_client.get("/tasks")
    assert response.status_code == 200
    assert response.json() == []


def test_task_created_on_one_instance_is_listed_on_another(  # AC-002.3
    make_app: MakeApp, clean_db: str
) -> None:
    one, other = make_app(), make_app()
    created = one.post("/tasks", json={"title": "Shared", "due_date": "2026-12-01"})
    assert created.status_code == 201
    assert _db_titles(clean_db) == ["Shared"]  # stored in Postgres, not in process memory
    listed = other.get("/tasks")
    assert listed.status_code == 200
    assert listed.json() == [created.json()]


def test_two_instances_starting_at_once_both_work(  # AC-002.4
    make_app: MakeApp, clean_db: str
) -> None:
    one, other = make_app(), make_app()
    statuses: dict[str, int] = {}

    def ready(name: str, c: TestClient) -> None:
        statuses[name] = c.get("/ready").status_code

    threads = [
        threading.Thread(target=ready, args=("one", one)),
        threading.Thread(target=ready, args=("other", other)),
    ]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=30)
    assert statuses == {"one": 200, "other": 200}
    with psycopg.connect(clean_db, autocommit=True) as conn:
        row = conn.execute("SELECT to_regclass('public.tasks')").fetchone()
    assert row is not None
    assert row[0] is not None  # the tasks table exists in the database
    for c in (one, other):
        assert c.post("/tasks", json={"title": "after start"}).status_code == 201
        assert c.get("/tasks").status_code == 200


def test_database_down_answers_503_and_stores_nothing(  # AC-002.5
    task_client: TestClient, db_down: DbDown
) -> None:
    with db_down():
        started = time.monotonic()
        posted = task_client.post("/tasks", json={"title": "ghost"})
        post_elapsed = time.monotonic() - started
        started = time.monotonic()
        listed = task_client.get("/tasks")
        get_elapsed = time.monotonic() - started
        assert posted.status_code == 503
        assert posted.json() == UNAVAILABLE
        assert listed.status_code == 503
        assert listed.json() == UNAVAILABLE
        assert post_elapsed < 5
        assert get_elapsed < 5
    after = task_client.get("/tasks")
    assert after.status_code == 200
    assert "ghost" not in [t["title"] for t in after.json()]


def test_unreachable_database_answers_503_within_5_seconds() -> None:  # AC-002.5
    from taskboard15_api.main import create_app

    c = TestClient(create_app("postgresql://u@127.0.0.1:1/x"))
    for method, kwargs in (("get", {}), ("post", {"json": {"title": "t"}})):
        started = time.monotonic()
        response = getattr(c, method)("/tasks", **kwargs)
        assert time.monotonic() - started < 5
        assert response.status_code == 503
        assert response.json() == UNAVAILABLE


def test_hanging_database_answers_503_within_5_seconds(hanging_db_url: str) -> None:  # AC-002.5
    from taskboard15_api.main import create_app

    c = TestClient(create_app(hanging_db_url))
    for method, kwargs in (("get", {}), ("post", {"json": {"title": "t"}})):
        started = time.monotonic()
        response = getattr(c, method)("/tasks", **kwargs)
        assert time.monotonic() - started < 5
        assert response.status_code == 503
        assert response.json() == UNAVAILABLE


def test_ready_follows_the_database_and_health_does_not(  # AC-002.6
    task_client: TestClient, db_down: DbDown
) -> None:
    assert task_client.get("/ready").status_code == 200
    with db_down():
        not_ready = task_client.get("/ready")
        assert not_ready.status_code == 503
        assert not_ready.json() == {"status": "not ready"}
        health = task_client.get("/health")
        assert health.status_code == 200
        assert health.json() == {"status": "ok"}
    recovered = task_client.get("/ready")  # same app object, no restart
    assert recovered.status_code == 200
    assert recovered.json() == {"status": "ready"}


def test_ready_is_503_for_unreachable_database() -> None:  # AC-002.6
    from taskboard15_api.main import create_app

    c = TestClient(create_app("postgresql://u@127.0.0.1:1/x"))
    response = c.get("/ready")
    assert response.status_code == 503
    assert response.json() == {"status": "not ready"}
    assert c.get("/health").status_code == 200


def test_create_then_list_last(task_client: TestClient) -> None:  # AC-002.7
    assert task_client.post("/tasks", json={"title": "Earlier"}).status_code == 201
    response = task_client.post("/tasks", json={"title": "Write report", "due_date": "2026-12-01"})
    assert response.status_code == 201
    body = response.json()
    assert isinstance(body["id"], str)
    assert body["id"]
    assert body["title"] == "Write report"
    assert body["due_date"] == "2026-12-01"
    listed = task_client.get("/tasks")
    assert listed.status_code == 200
    assert listed.json()[-1] == body
