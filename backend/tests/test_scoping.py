"""Behavioral tests for the Phase-1 scoping graph.

These exercise the real LangGraph machinery — checkpointer, ``interrupt()``,
``Command(resume=...)``, the cyclic deepen loop, and the ``Send`` fan-out into
`fetch_docs` — with **fake** discovery functions. No network, no LLM.
"""

from typing import Any

import pytest
from langchain_core.runnables import RunnableConfig
from langgraph.graph.state import CompiledStateGraph
from langgraph.types import Command

from app.generation.scoping import (
    MAX_DEEPEN_LEVELS,
    ResumePayload,
    ScopingState,
    build_scoping_graph,
)
from tests.fakes import fake_expand, fake_fetch


def _graph() -> CompiledStateGraph:
    return build_scoping_graph(expand_fn=fake_expand, fetch_fn=fake_fetch)


def _interrupt_payload(result: dict[str, Any]) -> dict[str, Any]:
    """Pull the single pending interrupt's payload out of an invoke result."""
    interrupts = result["__interrupt__"]
    assert len(interrupts) == 1
    return interrupts[0].value


def _start(
    graph: CompiledStateGraph, root_topic: str, thread_id: str
) -> dict[str, Any]:
    """Begin a scoping run; returns the first paused state (an interrupt)."""
    config: RunnableConfig = {"configurable": {"thread_id": thread_id}}
    initial: ScopingState = {
        "root_topic": root_topic,
        "tree": [],
        "selected_leaf_ids": [],
        "docs": [],
        "cursor_id": None,
        "depth": 0,
        "deeper": False,
    }
    return graph.invoke(initial, config)


def _resume(
    graph: CompiledStateGraph,
    thread_id: str,
    selected: list[str],
    deeper_into: str | None,
) -> dict[str, Any]:
    """Resume a paused run on `thread_id` with the human's pick."""
    config: RunnableConfig = {"configurable": {"thread_id": thread_id}}
    payload: ResumePayload = {"selected": selected, "deeper_into": deeper_into}
    cmd: Command[Any] = Command(resume=payload)
    return graph.invoke(cmd, config)


def test_first_pause_offers_root_frontier() -> None:
    payload = _interrupt_payload(_start(_graph(), "web development", "t-root"))

    assert payload["kind"] == "pick"
    assert payload["depth"] == 0
    assert payload["can_deepen"] is True
    assert {o["id"] for o in payload["options"]} == {"rest", "graphql", "react"}


def test_deepen_loops_back_and_fans_out_to_docs() -> None:
    """Pick + drill into React, pick at the deeper frontier, then fan out to docs.

    The deepened pick (React) is NOT a leaf; the picks that aren't deepened
    accumulate across both levels and each gets a fetched doc in the scope.
    """
    graph = _graph()
    _start(graph, "web development", "t-deepen")

    # Level 0: keep REST, drill into React.
    payload2 = _interrupt_payload(
        _resume(graph, "t-deepen", ["rest", "react"], "react")
    )
    assert payload2["depth"] == 1
    assert {o["id"] for o in payload2["options"]} == {
        "react/hooks",
        "react/jsx",
        "react/context",
    }

    # Level 1: keep Hooks + Context, stop -> fan out to fetch_docs.
    final = _resume(graph, "t-deepen", ["react/hooks", "react/context"], None)
    assert "__interrupt__" not in final

    scope = final["scope"]
    assert scope.root_topic == "web development"
    topics = {t.id: t for t in scope.topics}
    assert set(topics) == {"rest", "react/hooks", "react/context"}
    # React was drilled into, so it is not itself a leaf.
    assert "react" not in topics
    # Each leaf carries its fetched doc text + sources.
    assert topics["react/hooks"].doc_text == "docs for Hooks"
    assert topics["rest"].sources == ["https://example.test/rest"]


def test_resume_requires_same_thread_id() -> None:
    """The checkpointer keys on thread_id; a fresh thread has nothing to resume."""
    graph = _graph()
    _start(graph, "web development", "t-a")

    # No checkpoint for that thread -> the graph starts fresh with no initial
    # state and `expand` finds no root_topic.
    with pytest.raises(KeyError):
        _resume(graph, "t-does-not-exist", ["rest"], None)


def test_no_selection_finishes_with_empty_scope() -> None:
    """Picking nothing (and not deepening) skips the fan-out and yields no topics."""
    graph = _graph()
    _start(graph, "web development", "t-empty")

    final = _resume(graph, "t-empty", [], None)
    assert "__interrupt__" not in final
    assert final["scope"].topics == []


def test_deepen_is_capped() -> None:
    """After MAX_DEEPEN_LEVELS drills, can_deepen is false and further drill
    requests are ignored (treated as final picks)."""
    graph = _graph()

    payload = _interrupt_payload(_start(graph, "web development", "t-cap"))
    # Drill the maximum number of times.
    cursor = "react"
    for level in range(MAX_DEEPEN_LEVELS):
        assert payload["depth"] == level
        assert payload["can_deepen"] is True
        payload = _interrupt_payload(_resume(graph, "t-cap", [cursor], cursor))
        cursor = payload["options"][0]["id"]

    # Now at the cap: deepening is disabled.
    assert payload["depth"] == MAX_DEEPEN_LEVELS
    assert payload["can_deepen"] is False

    # A drill request here is ignored and the graph finishes.
    final = _resume(graph, "t-cap", [cursor], cursor)
    assert "__interrupt__" not in final
    assert any(t.id == cursor for t in final["scope"].topics)
