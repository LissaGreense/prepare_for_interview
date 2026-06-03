"""Pydantic models for the quiz domain."""

from pydantic import BaseModel


class Question(BaseModel):
    """A single-choice quiz question.

    `id` and `topic` are derived from the filesystem (filename stem and parent
    folder) by the corpus reader, not stored in the question JSON.
    """

    id: str
    topic: str
    question: str
    options: list[str]
    correct: int
    explanation: str | None = None
