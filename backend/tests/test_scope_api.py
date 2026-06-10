"""API tests for the scoping bridge endpoints.

The service's graph singleton is swapped for a fake-injected graph so these run
offline (no network, no LLM).
"""

from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.generation import service
from app.generation.scoping import build_scoping_graph
from app.main import app
from tests.fakes import fake_expand, fake_fetch


@pytest.fixture
def client(monkeypatch: Any) -> TestClient:
    fake_graph = build_scoping_graph(expand_fn=fake_expand, fetch_fn=fake_fetch)
    monkeypatch.setattr(service, "_GRAPH", fake_graph)
    return TestClient(app)


def test_start_returns_first_pick(client: TestClient) -> None:
    resp = client.post("/scope/start", json={"root_topic": "web development"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "awaiting_pick"
    assert body["thread_id"]
    assert body["pick"]["depth"] == 0
    assert body["pick"]["can_deepen"] is True
    assert {o["id"] for o in body["pick"]["options"]} == {"rest", "graphql", "react"}


def test_full_flow_start_deepen_resume_to_scope(client: TestClient) -> None:
    start = client.post("/scope/start", json={"root_topic": "web development"}).json()
    thread_id = start["thread_id"]

    # Drill into React.
    deeper = client.post(
        f"/scope/{thread_id}/resume",
        json={"selected": ["rest", "react"], "deeper_into": "react"},
    ).json()
    assert deeper["status"] == "awaiting_pick"
    assert deeper["pick"]["depth"] == 1
    assert {o["id"] for o in deeper["pick"]["options"]} == {
        "react/hooks",
        "react/jsx",
        "react/context",
    }

    # Finish -> scope with fetched docs.
    done = client.post(
        f"/scope/{thread_id}/resume",
        json={"selected": ["react/hooks", "react/context"], "deeper_into": None},
    ).json()
    assert done["status"] == "done"
    topics = {t["id"]: t for t in done["scope"]["topics"]}
    assert set(topics) == {"rest", "react/hooks", "react/context"}
    assert topics["react/hooks"]["doc_text"] == "docs for Hooks"


def test_resume_unknown_thread_is_404(client: TestClient) -> None:
    resp = client.post(
        "/scope/nope-not-a-thread/resume",
        json={"selected": ["rest"], "deeper_into": None},
    )
    assert resp.status_code == 404
