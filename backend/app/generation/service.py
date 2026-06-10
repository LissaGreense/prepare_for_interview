"""HTTP-facing service for the scoping graph.

Thin wrapper over the compiled LangGraph (and its in-process `MemorySaver`) so
FastAPI handlers stay dumb. The `thread_id` is the session key — the checkpointer
persists each paused run under it, so "resume" just re-invokes the same graph with
the same `thread_id`.
"""

from __future__ import annotations

import uuid
from typing import Any, Literal

from langgraph.types import Command
from pydantic import BaseModel

from .scoping import StudyScope, build_scoping_graph

# Lazily-built singleton so the graph (and its checkpointer) persist across
# requests. Tests swap this for a fake-injected graph.
_GRAPH: Any = None


def _graph() -> Any:
    global _GRAPH
    if _GRAPH is None:
        _GRAPH = build_scoping_graph()
    return _GRAPH


class PickOption(BaseModel):
    """One selectable topic at the current frontier."""

    id: str
    label: str
    kind: str


class PickPrompt(BaseModel):
    """What the UI renders when the graph pauses for a human pick."""

    question: str
    depth: int
    can_deepen: bool
    options: list[PickOption]


class ScopeState(BaseModel):
    """Discriminated response: either awaiting a pick, or done with a scope."""

    status: Literal["awaiting_pick", "done"]
    thread_id: str
    pick: PickPrompt | None = None
    scope: StudyScope | None = None


class UnknownThreadError(Exception):
    """Raised when resuming a `thread_id` with no persisted run."""


def _interpret(thread_id: str, result: dict[str, Any]) -> ScopeState:
    """Map a graph invoke result to the API response."""
    if "__interrupt__" in result:
        payload = result["__interrupt__"][0].value
        return ScopeState(
            status="awaiting_pick",
            thread_id=thread_id,
            pick=PickPrompt(
                question=payload["question"],
                depth=payload["depth"],
                can_deepen=payload["can_deepen"],
                options=payload["options"],
            ),
        )
    return ScopeState(
        status="done",
        thread_id=thread_id,
        scope=StudyScope(**result["scope"]),
    )


def start(root_topic: str) -> ScopeState:
    """Begin a scoping session; returns the first pick prompt."""
    thread_id = uuid.uuid4().hex
    config = {"configurable": {"thread_id": thread_id}}
    initial: dict[str, Any] = {
        "root_topic": root_topic,
        "tree": [],
        "selected_leaf_ids": [],
        "docs": [],
        "cursor_id": None,
        "depth": 0,
        "deeper": False,
    }
    return _interpret(thread_id, _graph().invoke(initial, config))


def resume(thread_id: str, selected: list[str], deeper_into: str | None) -> ScopeState:
    """Resume a paused session with the user's pick. Returns the next pick or scope."""
    config = {"configurable": {"thread_id": thread_id}}
    graph = _graph()
    # Reject unknown threads up front: an unresumed thread has no persisted
    # checkpoint (no `next` nodes). Relying on a downstream node crashing would
    # both couple us to that node's internals and mask genuine errors.
    if not graph.get_state(config).next:
        raise UnknownThreadError(thread_id)
    cmd: Command[Any] = Command(
        resume={"selected": selected, "deeper_into": deeper_into}
    )
    return _interpret(thread_id, graph.invoke(cmd, config))
