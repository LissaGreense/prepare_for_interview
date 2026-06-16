"""Tests for Phase-2 generation, mocking only the LLM boundary (no network/LLM)."""

from pytest import MonkeyPatch

from app.generation import generation
from app.generation.generation import (
    QuestionBatch,
    QuestionDraft,
    generate_for_topic,
)
from app.generation.scoping import ScopeTopic


class _FakeRunnable:
    """Stands in for the structured-output runnable; returns a fixed batch."""

    def __init__(self, result: QuestionBatch) -> None:
        self._result = result

    def invoke(self, _prompt: object) -> QuestionBatch:
        return self._result


def _topic(doc_text: str = "docs for REST") -> ScopeTopic:
    return ScopeTopic(id="rest", label="REST API", doc_text=doc_text, sources=[])


def _draft(correct: int = 0, options: int = 4) -> QuestionDraft:
    return QuestionDraft(
        question=f"Q with correct={correct}?",
        options=[f"opt{i}" for i in range(options)],
        correct=correct,
        explanation="because",
    )


def _patch_llm(monkeypatch: MonkeyPatch, batch: QuestionBatch) -> None:
    monkeypatch.setattr(
        generation, "structured", lambda schema, **k: _FakeRunnable(batch)
    )


def test_returns_valid_drafts(monkeypatch: MonkeyPatch) -> None:
    _patch_llm(monkeypatch, QuestionBatch(questions=[_draft(0), _draft(3)]))

    drafts = generate_for_topic(_topic(), count=2)

    assert [d.correct for d in drafts] == [0, 3]


def test_drops_structurally_invalid_drafts(monkeypatch: MonkeyPatch) -> None:
    _patch_llm(
        monkeypatch,
        QuestionBatch(
            questions=[
                _draft(0),  # valid
                _draft(9),  # correct out of range -> dropped
                _draft(0, options=3),  # wrong option count -> dropped
            ]
        ),
    )

    drafts = generate_for_topic(_topic())

    assert len(drafts) == 1
    assert drafts[0].correct == 0


def test_skips_topic_with_no_docs(monkeypatch: MonkeyPatch) -> None:
    def _boom(_schema: object, **_k: object) -> object:
        raise AssertionError("LLM must not be called for an empty-doc topic")

    monkeypatch.setattr(generation, "structured", _boom)

    assert generate_for_topic(_topic(doc_text="   ")) == []
