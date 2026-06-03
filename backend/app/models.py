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


class TopicManifest(BaseModel):
    """Display metadata for a topic, read from a `topic.json` manifest.

    All fields are optional; a topic works without a manifest. Stored in the
    topic folder, separate from the question files.
    """

    title: str | None = None
    icon: str | None = None
    description: str | None = None


class Topic(BaseModel):
    """A topic's display metadata plus how many valid questions it has on disk.

    `topic` is the folder name (the id used by `/quiz`). `title`, `icon`, and
    `description` come from the folder's optional `topic.json` manifest; `title`
    falls back to the folder name when no manifest provides one.
    """

    topic: str
    title: str
    icon: str | None = None
    description: str | None = None
    count: int
