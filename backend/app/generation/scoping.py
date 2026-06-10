"""Phase 1 — interactive topic-scoping graph (LangGraph).

Flow: ``expand -> pick (interrupt) -> [deeper? loop to expand : fan-out fetch_docs]
-> assemble -> END``.

The user picks topics at each frontier and may "go deeper" into one. Picks that
aren't deepened become final leaves; the deepened pick's children become the next
frontier. Selections accumulate across levels, bounded by ``MAX_DEEPEN_LEVELS``.
On finish, the selected leaves fan out (``Send``) to parallel ``fetch_docs`` tasks
and `assemble` collapses the results into a `StudyScope` for Phase 2 (generation).

The discovery side (`expand_fn`, `fetch_fn`) is injected so the graph mechanics
can be tested offline with fakes; the defaults do real search + LLM + doc fetch.
"""

from __future__ import annotations

import operator
from collections.abc import Callable
from typing import Annotated, Literal, TypedDict

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph
from langgraph.types import Send, interrupt
from pydantic import BaseModel

#: How many times the user may "drill deeper" past the root frontier. Bounds the
#: cyclic ``pick -> expand`` edge so a runaway loop can't blow ``recursion_limit``.
MAX_DEEPEN_LEVELS = 3


class TopicNode(TypedDict):
    """One node in the discovered topic tree.

    `id` is a stable slug used everywhere as the identity; `parent_id` links it
    to the frontier it was discovered under (``None`` at the root level).
    """

    id: str
    label: str
    kind: Literal["subtopic", "technology"]
    parent_id: str | None


class FetchedDoc(TypedDict):
    """Documentation text fetched for one selected leaf topic."""

    topic_id: str
    text: str
    sources: list[str]


class FetchPayload(TypedDict):
    """Per-leaf payload handed to ``fetch_docs`` by each ``Send`` in the fan-out."""

    topic_id: str
    label: str


class ScopeTopic(BaseModel):
    """A selected leaf topic plus the documentation gathered for it."""

    id: str
    label: str
    doc_text: str
    sources: list[str]


class StudyScope(BaseModel):
    """Phase-1 output: the curated leaves + their docs, handed to generation."""

    root_topic: str
    topics: list[ScopeTopic]


class ScopingState(TypedDict, total=False):
    """Graph state.

    Reducers matter: `tree`, `selected_leaf_ids`, and `docs` use ``operator.add``
    so each expand pass, each pick, and each parallel fetch *append* rather than
    clobber. Routing/cursor fields overwrite — the latest pick is authoritative.
    """

    root_topic: str
    tree: Annotated[list[TopicNode], operator.add]
    selected_leaf_ids: Annotated[list[str], operator.add]
    docs: Annotated[list[FetchedDoc], operator.add]
    cursor_id: str | None
    depth: int
    deeper: bool
    scope: StudyScope


#: (query, parent_id) -> child topic nodes. `query` is the root topic at the top
#: level, otherwise the label of the node being deepened.
ExpandFn = Callable[[str, str | None], list[TopicNode]]
#: (topic_id, label) -> documentation for one selected leaf.
FetchFn = Callable[[str, str], FetchedDoc]


def _label_of(tree: list[TopicNode], node_id: str | None) -> str:
    for n in tree:
        if n["id"] == node_id:
            return n["label"]
    return node_id or ""


def build_scoping_graph(
    *,
    expand_fn: ExpandFn | None = None,
    fetch_fn: FetchFn | None = None,
) -> CompiledStateGraph:
    """Compile the scoping graph with an in-memory checkpointer.

    `expand_fn`/`fetch_fn` default to the real (search + LLM + doc-fetch)
    implementations; tests inject fakes to stay offline. The checkpointer is
    mandatory for ``interrupt()``; callers must pass a ``thread_id`` in
    ``config["configurable"]`` and reuse it on resume.
    """
    if expand_fn is None or fetch_fn is None:
        from .discovery import default_expand, default_fetch

        expand_fn = expand_fn or default_expand
        fetch_fn = fetch_fn or default_fetch

    def expand(state: ScopingState) -> ScopingState:
        """Discover the children of the current frontier (`cursor_id`, ``None`` = root).

        Idempotent: drops nodes already in `tree`, so a re-run can't duplicate a
        frontier.
        """
        parent_id = state.get("cursor_id")
        tree = state.get("tree", [])
        query = state["root_topic"] if parent_id is None else _label_of(tree, parent_id)
        known = {n["id"] for n in tree}
        children = [n for n in expand_fn(query, parent_id) if n["id"] not in known]
        return {"tree": children}

    def pick(state: ScopingState) -> ScopingState:
        """Pause for the human to select topics at the current frontier.

        Everything before ``interrupt()`` is a pure read of state, so the node is
        safe to re-run when the graph resumes. The resume payload is the return
        value of ``interrupt()``.
        """
        cursor_id = state.get("cursor_id")
        depth = state.get("depth", 0)
        frontier = [n for n in state.get("tree", []) if n["parent_id"] == cursor_id]

        answer = interrupt(
            {
                "kind": "pick",
                "question": "Select the parts to cover. Optionally drill into one.",
                "depth": depth,
                "can_deepen": depth < MAX_DEEPEN_LEVELS,
                "options": [
                    {"id": n["id"], "label": n["label"], "kind": n["kind"]}
                    for n in frontier
                ],
            }
        )

        selected: list[str] = list(answer.get("selected", []))
        deeper_into = answer.get("deeper_into")
        # Honor the cap: at max depth a "go deeper" request is a final pick.
        if depth >= MAX_DEEPEN_LEVELS:
            deeper_into = None

        finalized = [sid for sid in selected if sid != deeper_into]
        return {
            "selected_leaf_ids": finalized,  # appended via operator.add
            "cursor_id": deeper_into,
            "deeper": deeper_into is not None,
            "depth": depth + (1 if deeper_into else 0),
        }

    def route_after_pick(state: ScopingState) -> str | list[Send]:
        """Loop back to `expand` to drill, else fan out to `fetch_docs` per leaf."""
        if state.get("deeper"):
            return "expand"
        leaves = state.get("selected_leaf_ids", [])
        if not leaves:
            return "assemble"
        tree = state.get("tree", [])
        return [
            Send("fetch_docs", {"topic_id": tid, "label": _label_of(tree, tid)})
            for tid in leaves
        ]

    def fetch_docs(payload: FetchPayload) -> ScopingState:
        """Fetch docs for one selected leaf (runs once per ``Send``, in parallel)."""
        doc = fetch_fn(payload["topic_id"], payload["label"])
        return {"docs": [doc]}  # appended via operator.add across parallel branches

    def assemble(state: ScopingState) -> ScopingState:
        """Collapse accumulated docs + picks into the Phase-1 `StudyScope`."""
        tree = state.get("tree", [])
        scope = StudyScope(
            root_topic=state.get("root_topic", ""),
            topics=[
                ScopeTopic(
                    id=doc["topic_id"],
                    label=_label_of(tree, doc["topic_id"]),
                    doc_text=doc["text"],
                    sources=doc["sources"],
                )
                for doc in state.get("docs", [])
            ],
        )
        return {"scope": scope}

    builder = StateGraph(ScopingState)
    builder.add_node("expand", expand)
    builder.add_node("pick", pick)
    # fetch_docs receives a per-Send payload (not the full state), which
    # LangGraph's node typing can't express.
    builder.add_node("fetch_docs", fetch_docs)  # type: ignore[arg-type]
    builder.add_node("assemble", assemble)

    builder.add_edge(START, "expand")
    builder.add_edge("expand", "pick")
    builder.add_conditional_edges(
        "pick", route_after_pick, ["expand", "fetch_docs", "assemble"]
    )
    builder.add_edge("fetch_docs", "assemble")
    builder.add_edge("assemble", END)

    return builder.compile(checkpointer=MemorySaver())
