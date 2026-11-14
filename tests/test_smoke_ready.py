"""Smoke test for spec 002 (AC-002.6): the deployed service reaches its database. Read-only."""

from __future__ import annotations

import httpx
import pytest


@pytest.mark.smoke
def test_ac_002_6_ready_answers_ready_smoke(smoke_base_url: str) -> None:
    response = httpx.get(smoke_base_url + "/ready", timeout=10)
    assert response.status_code == 200
    assert response.json() == {"status": "ready"}
