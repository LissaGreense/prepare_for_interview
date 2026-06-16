"""API tests for the scoping bridge endpoints.

The service's graph singleton is swapped for a fake-injected graph so these run
offline (no network, no LLM).
"""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from pytest import MonkeyPatch

from app.generation import generation, service, writer
from app.generation.generation import QuestionBatch, QuestionDraft
from app.generation.scoping import build_scoping_graph
from app.main import app
from tests.fakes import fake_expand, fake_fetch


@pytest.fixture
def client(monkeypatch: MonkeyPatch) -> TestClient:
    fake_graph = build_scoping_graph(expand_fn=fake_expand, fetch_fn=fake_fetch)
    monkeypatch.setattr(service, "_GRAPH", fake_graph)
    return TestClient(app)


def _drive_to_scope(client: TestClient) -> str:
    """Run a session through to a finished scope; returns its thread_id."""
    thread_id = str(
        client.post("/scope/start", json={"root_topic": "web development"}).json()[
            "thread_id"
        ]
    )
    client.post(
        f"/scope/{thread_id}/resume",
        json={"selected": ["rest", "react"], "deeper_into": "react"},
    )
    client.post(
        f"/scope/{thread_id}/resume",
        json={"selected": ["react/hooks", "react/context"], "deeper_into": None},
    )
    return thread_id


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


def test_generate_writes_questions_per_topic(
    client: TestClient, monkeypatch: MonkeyPatch, tmp_path: Path
) -> None:
    # Offline: fake the LLM, and write into a tmp corpus dir.
    batch = QuestionBatch(
        questions=[
            QuestionDraft(
                question=f"Q{i}?",
                options=["a", "b", "c", "d"],
                correct=0,
                explanation="why",
            )
            for i in range(3)
        ]
    )
    monkeypatch.setattr(
        generation,
        "structured",
        lambda schema, **k: type("R", (), {"invoke": lambda self, p: batch})(),
    )
    monkeypatch.setattr(writer, "QUESTIONS_DIR", tmp_path)

    thread_id = _drive_to_scope(client)
    resp = client.post(f"/scope/{thread_id}/generate")

    assert resp.status_code == 200
    body = resp.json()
    assert body["root_topic"] == "web development"
    # Three scoped topics (rest, react/hooks, react/context), 3 questions each.
    assert {t["topic_id"] for t in body["topics"]} == {
        "rest",
        "react/hooks",
        "react/context",
    }
    assert body["total"] == 9


def test_generate_unknown_thread_is_404(client: TestClient) -> None:
    assert client.post("/scope/nope/generate").status_code == 404


def test_generate_before_scope_ready_is_409(client: TestClient) -> None:
    thread_id = client.post(
        "/scope/start", json={"root_topic": "web development"}
    ).json()["thread_id"]

    # Session exists but is still awaiting the first pick.
    assert client.post(f"/scope/{thread_id}/generate").status_code == 409
