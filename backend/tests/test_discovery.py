"""Tests for the real discovery functions, mocking only the external boundary
(DuckDuckGo search, the LLM, and the web loader). No network, no LLM.
"""

from typing import Any

from langchain_core.documents import Document

from app.generation import discovery
from app.generation.discovery import Subtopic, SubtopicList


class _FakeRunnable:
    """Stands in for the structured-output runnable; returns a fixed result."""

    def __init__(self, result: Any) -> None:
        self._result = result

    def invoke(self, _prompt: Any) -> Any:
        return self._result


def test_slugify_and_child_id() -> None:
    assert discovery._slugify("REST API!") == "rest-api"
    assert discovery._slugify("Hooks & State") == "hooks-state"
    assert discovery._child_id(None, "React") == "react"
    assert discovery._child_id("react", "Custom Hooks") == "react/custom-hooks"


def test_default_expand_builds_topic_nodes(monkeypatch: Any) -> None:
    monkeypatch.setattr(
        discovery, "_search", lambda q, **k: [{"title": "t", "snippet": "s"}]
    )
    result = SubtopicList(
        subtopics=[
            Subtopic(label="REST API", kind="subtopic"),
            Subtopic(label="React", kind="technology"),
        ]
    )
    monkeypatch.setattr(
        discovery, "structured", lambda schema, **k: _FakeRunnable(result)
    )

    nodes = discovery.default_expand("web development", None)

    assert [n["id"] for n in nodes] == ["rest-api", "react"]
    assert all(n["parent_id"] is None for n in nodes)
    assert nodes[1]["kind"] == "technology"


def test_default_expand_nests_child_ids_under_parent(monkeypatch: Any) -> None:
    monkeypatch.setattr(discovery, "_search", lambda q, **k: [])
    result = SubtopicList(subtopics=[Subtopic(label="Hooks", kind="subtopic")])
    monkeypatch.setattr(
        discovery, "structured", lambda schema, **k: _FakeRunnable(result)
    )

    nodes = discovery.default_expand("React", "react")

    assert nodes[0]["id"] == "react/hooks"
    assert nodes[0]["parent_id"] == "react"


def test_default_fetch_loads_and_chunks(monkeypatch: Any) -> None:
    monkeypatch.setattr(
        discovery,
        "_search",
        lambda q, **k: [{"link": "https://a.test"}, {"link": "https://b.test"}],
    )

    class FakeLoader:
        def __init__(self, urls: Any) -> None:
            self.urls = urls

        def load(self) -> list[Document]:
            return [Document(page_content="hello world " * 50, metadata={})]

    monkeypatch.setattr(discovery, "WebBaseLoader", FakeLoader)

    doc = discovery.default_fetch("rest", "REST API")

    assert doc["topic_id"] == "rest"
    assert doc["sources"] == ["https://a.test", "https://b.test"]
    assert "hello world" in doc["text"]


def test_default_fetch_with_no_search_results(monkeypatch: Any) -> None:
    monkeypatch.setattr(discovery, "_search", lambda q, **k: [])

    doc = discovery.default_fetch("x", "X")

    assert doc["text"] == ""
    assert doc["sources"] == []


def test_default_fetch_survives_loader_failure(monkeypatch: Any) -> None:
    monkeypatch.setattr(
        discovery, "_search", lambda q, **k: [{"link": "https://a.test"}]
    )

    class BoomLoader:
        def __init__(self, urls: Any) -> None:
            pass

        def load(self) -> list[Document]:
            raise RuntimeError("network down")

    monkeypatch.setattr(discovery, "WebBaseLoader", BoomLoader)

    doc = discovery.default_fetch("rest", "REST API")

    assert doc["text"] == ""  # failure degrades to empty, doesn't crash the scope
    assert doc["sources"] == ["https://a.test"]
