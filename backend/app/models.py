"""Pydantic models for the quiz domain."""

from pydantic import BaseModel, model_validator


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

    @model_validator(mode="after")
    def _correct_indexes_an_option(self) -> "Question":
        """`correct` must be a valid zero-based index into `options`."""
        if not 0 <= self.correct < len(self.options):
            raise ValueError(
                f"correct={self.correct} is out of range for "
                f"{len(self.options)} option(s)"
            )
        return self


class Topic(BaseModel):
    """A topic and how many valid questions it currently has on disk."""

    topic: str
    count: int
