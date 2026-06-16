"""Phase 2 — question generation.

Consume one Phase-1 `ScopeTopic` (a leaf topic plus its fetched documentation) and
emit quiz questions in the on-disk shape. One structured LLM call per topic returns
a whole batch — the same one-call-returns-many move as `discovery.SubtopicList` —
grounded in the topic's `doc_text` so the model isn't free-styling.

Iteration 1 is a straight pipeline: generate -> filter-validate -> (caller writes).
Invalid drafts are dropped and logged, exactly like `corpus` skips malformed files;
auto-retry on a bad draft is the iteration-2 LangGraph upgrade.
"""

from __future__ import annotations

import logging

from pydantic import BaseModel, Field, ValidationError

from ..models import Question
from .llm import structured
from .scoping import ScopeTopic

_log = logging.getLogger(__name__)

#: Every question is a 4-option single-choice MCQ in iteration 1.
OPTIONS_PER_QUESTION = 4


class QuestionDraft(BaseModel):
    """One generated question, in the on-disk content shape.

    Mirrors `models.Question` minus the filesystem-derived `id`/`topic` — those are
    assigned by the writer from the file path, never emitted by the model.
    """

    question: str = Field(description="A clear, self-contained single-choice question")
    options: list[str] = Field(
        description=f"Exactly {OPTIONS_PER_QUESTION} distinct, plausible answer choices"
    )
    correct: int = Field(
        description="0-based index into `options` of the single correct answer"
    )
    explanation: str = Field(
        description="1-2 sentences on why the correct option is right"
    )


class QuestionBatch(BaseModel):
    """Structured-output schema for one generation call: N questions at once."""

    questions: list[QuestionDraft] = Field(
        description="The generated interview questions"
    )


def _is_valid(draft: QuestionDraft, label: str) -> bool:
    """Structural validation only (iteration 1).

    Enforces the fixed option count and reuses the `Question` model validator for the
    `0 <= correct < len(options)` invariant — same rule the corpus reader applies on
    read, so a generated file can never be one a later load would silently skip. A
    wrong-but-in-range `correct` is *not* caught here; that's an iteration-2 concern.
    """
    if len(draft.options) != OPTIONS_PER_QUESTION:
        _log.warning(
            "dropping draft for %r: %d options, expected %d",
            label,
            len(draft.options),
            OPTIONS_PER_QUESTION,
        )
        return False
    try:
        Question(id="draft", topic="draft", **draft.model_dump())
    except ValidationError as exc:
        _log.warning("dropping invalid draft for %r: %s", label, exc)
        return False
    return True


def _prompt(topic: ScopeTopic, count: int) -> str:
    return (
        "You are writing single-choice interview-prep quiz questions.\n"
        f'Write {count} distinct questions on the topic "{topic.label}".\n'
        f"Each question has exactly {OPTIONS_PER_QUESTION} answer options with one "
        "correct answer; `correct` is the 0-based index of that option. Keep "
        "questions self-contained, unambiguous, and at interview difficulty. Ground "
        "every question in the documentation below — do not invent facts beyond it.\n\n"
        f"Documentation for {topic.label}:\n{topic.doc_text}"
    )


def generate_for_topic(topic: ScopeTopic, *, count: int = 5) -> list[QuestionDraft]:
    """Generate up to `count` valid questions for one scoped topic.

    Returns only structurally-valid drafts (invalid ones are dropped and logged), so
    the result may be shorter than `count`. A topic with no fetched documentation is
    skipped entirely — generating from a bare label is pure hallucination.
    """
    if not topic.doc_text.strip():
        _log.warning("skipping %r: no doc_text to ground generation", topic.label)
        return []
    batch = structured(QuestionBatch).invoke(_prompt(topic, count))
    return [d for d in batch.questions if _is_valid(d, topic.label)]
