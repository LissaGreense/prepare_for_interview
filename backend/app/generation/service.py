"""HTTP-facing service for the scoping graph.

Thin wrapper over the compiled LangGraph (and its in-process `MemorySaver`) so
FastAPI handlers stay dumb. The `thread_id` is the session key — the checkpointer
persists each paused run under it, so "resume" just re-invokes the same graph with
the same `thread_id`.
"""

from __future__ import annotations

import uuid
from typing import Any, Literal

from langchain_core.runnables import RunnableConfig
from langgraph.types import Command
from pydantic import BaseModel

from .scoping import (
    ResumePayload,
    ScopingGraph,
    ScopingState,
    StudyScope,
    build_scoping_graph,
)

# Lazily-built singleton so the graph (and its checkpointer) persist across
# requests. Tests swap this for a fake-injected graph.
_GRAPH: ScopingGraph | None = None


def _graph() -> ScopingGraph:
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


class ScopeNotReadyError(Exception):
    """Raised when generation is requested before a session reached its scope."""


class TopicGeneration(BaseModel):
    """How many questions were written for one scoped topic."""

    topic_id: str
    label: str
    written: int


class GenerationResult(BaseModel):
    """Summary of a generation run across all topics in a scope."""

    thread_id: str
    root_topic: str
    topics: list[TopicGeneration]
    total: int


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
        # `assemble` stores a StudyScope; across a checkpoint it round-trips as a
        # dict. model_validate accepts either.
        scope=StudyScope.model_validate(result["scope"]),
    )


def start(root_topic: str) -> ScopeState:
    """Begin a scoping session; returns the first pick prompt."""
    thread_id = uuid.uuid4().hex
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
    return _interpret(thread_id, _graph().invoke(initial, config))


def resume(thread_id: str, selected: list[str], deeper_into: str | None) -> ScopeState:
    """Resume a paused session with the user's pick. Returns the next pick or scope."""
    config: RunnableConfig = {"configurable": {"thread_id": thread_id}}
    graph = _graph()
    # Reject unknown threads up front: an unresumed thread has no persisted
    # checkpoint (no `next` nodes). Relying on a downstream node crashing would
    # both couple us to that node's internals and mask genuine errors.
    if not graph.get_state(config).next:
        raise UnknownThreadError(thread_id)
    payload: ResumePayload = {"selected": selected, "deeper_into": deeper_into}
    cmd: Command[Any] = Command(resume=payload)
    return _interpret(thread_id, graph.invoke(cmd, config))


def generate(thread_id: str, *, count: int = 5) -> GenerationResult:
    """Generate and persist questions for a finished scoping session.

    Reads the `StudyScope` the graph stored under `thread_id`, generates questions
    per topic (grounded in each topic's fetched docs), writes them to the corpus, and
    returns per-topic counts.

    Raises:
        UnknownThreadError: No persisted run for this `thread_id`.
        ScopeNotReadyError: The session exists but hasn't reached its scope yet.
    """
    from .generation import generate_for_topic
    from .writer import write_questions

    config: RunnableConfig = {"configurable": {"thread_id": thread_id}}
    state = _graph().get_state(config)
    if not state.values:
        raise UnknownThreadError(thread_id)
    raw_scope = state.values.get("scope")
    if raw_scope is None:
        raise ScopeNotReadyError(thread_id)

    scope = StudyScope.model_validate(raw_scope)
    results: list[TopicGeneration] = []
    for topic in scope.topics:
        drafts = generate_for_topic(topic, count=count)
        written = write_questions(topic.label, drafts, title=topic.label)
        results.append(
            TopicGeneration(topic_id=topic.id, label=topic.label, written=len(written))
        )
    return GenerationResult(
        thread_id=thread_id,
        root_topic=scope.root_topic,
        topics=results,
        total=sum(r.written for r in results),
    )
