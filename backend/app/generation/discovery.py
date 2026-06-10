"""Real discovery: search + LLM expansion and documentation fetch.

These are the default `expand_fn`/`fetch_fn` for the scoping graph. They use a
free DuckDuckGo search (no API key) to stay grounded/current, the configured
chat model for structured extraction, and `WebBaseLoader` to pull doc text.
"""

from __future__ import annotations

import logging
import os
import re
import time
from typing import Any, Literal, cast

from langchain_community.document_loaders import WebBaseLoader
from langchain_community.tools import DuckDuckGoSearchResults
from langchain_text_splitters import RecursiveCharacterTextSplitter
from pydantic import BaseModel, Field

from .llm import structured
from .scoping import FetchedDoc, TopicNode

_log = logging.getLogger(__name__)

# WebBaseLoader nags if this is unset; identify our requests politely.
os.environ.setdefault("USER_AGENT", "prepare-for-interview-quizgen")

_SEARCH = DuckDuckGoSearchResults(output_format="list", num_results=6)
_MAX_DOC_CHUNKS = 8  # cap doc context per topic so we don't stuff huge pages


class Subtopic(BaseModel):
    """One discovered sub-area of a topic."""

    label: str = Field(description="Short human name, e.g. 'REST API' or 'React'")
    kind: Literal["subtopic", "technology"] = Field(
        description="'technology' for a named tool/framework/library, else 'subtopic'"
    )


class SubtopicList(BaseModel):
    """Structured-output schema for one expansion pass."""

    subtopics: list[Subtopic] = Field(description="4-7 distinct sub-areas")


def _slugify(label: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", label.lower()).strip("-")
    return slug or "topic"


def _child_id(parent_id: str | None, label: str) -> str:
    slug = _slugify(label)
    return f"{parent_id}/{slug}" if parent_id else slug


def _search(query: str, *, retries: int = 3) -> list[dict[str, Any]]:
    """DuckDuckGo search with simple linear backoff (it rate-limits unpredictably)."""
    for attempt in range(retries):
        try:
            return cast(list[dict[str, Any]], _SEARCH.invoke(query))
        except Exception as exc:
            if attempt == retries - 1:
                _log.warning(
                    "search gave up for %r after %d tries: %s", query, retries, exc
                )
                return []
            time.sleep(1.5 * (attempt + 1))
    return []


def default_expand(query: str, parent_id: str | None) -> list[TopicNode]:
    """Break `query` into 4-7 interview sub-areas, grounded by a web search."""
    hits = _search(f"{query} core subtopics and key technologies to learn")
    context = "\n".join(
        f"- {h.get('title', '')}: {h.get('snippet', '')}" for h in hits[:5]
    )
    prompt = (
        "You are scoping an interview-prep study plan.\n"
        f'Break the topic "{query}" into 4-7 distinct sub-areas a candidate would '
        "be quizzed on. Prefer concrete, well-known areas over vague ones. Mark "
        "each as 'technology' (a named tool/framework/library) or 'subtopic' "
        "(a concept/area).\n\n"
        f"Recent search context (use it to stay current):\n{context or '(none)'}"
    )
    result = cast(SubtopicList, structured(SubtopicList).invoke(prompt))
    return [
        TopicNode(
            id=_child_id(parent_id, st.label),
            label=st.label,
            kind=st.kind,
            parent_id=parent_id,
        )
        for st in result.subtopics
    ]


def default_fetch(topic_id: str, label: str) -> FetchedDoc:
    """Fetch and chunk documentation text for one selected leaf topic."""
    hits = _search(f"{label} official documentation")
    urls = [h["link"] for h in hits[:2] if h.get("link")]
    text = ""
    if urls:
        try:
            docs = WebBaseLoader(urls).load()
            chunks = RecursiveCharacterTextSplitter(
                chunk_size=1000, chunk_overlap=200
            ).split_documents(docs)
            text = "\n\n".join(c.page_content for c in chunks[:_MAX_DOC_CHUNKS])
        except Exception as exc:
            # a flaky page shouldn't sink the whole scope — degrade to empty
            _log.warning("doc fetch failed for %r (%s): %s", label, urls, exc)
            text = ""
    return FetchedDoc(topic_id=topic_id, text=text, sources=urls)
