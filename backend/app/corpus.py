"""Read quiz questions from disk.

The filesystem is the source of truth: each topic is a folder under the
questions directory, and each question is one JSON file whose stem is the
question id. Files are read per request (no startup cache) so newly added
files appear immediately.
"""

import json
import logging
from pathlib import Path

from pydantic import ValidationError

from .models import Question, Topic

logger = logging.getLogger(__name__)

# Single swappable place for the corpus root. Resolved relative to this source
# file (app -> backend -> repo root) so it does not depend on the process CWD.
# A later task can point the loader at a fixture directory by passing `base`.
QUESTIONS_DIR = Path(__file__).resolve().parents[2] / "questions"


class TopicNotFoundError(Exception):
    """Raised when a requested topic has no corresponding folder on disk."""


def _read_question(file: Path, topic: str) -> Question | None:
    """Parse and validate one question file.

    Returns the Question, or None if the file is malformed (bad JSON, schema
    violation, or an out-of-range `correct` index). Malformed files are logged
    and skipped so a single bad file never breaks its topic.
    """
    try:
        data = json.loads(file.read_text())
        return Question(id=file.stem, topic=topic, **data)
    except (json.JSONDecodeError, ValidationError, TypeError) as exc:
        logger.warning("Skipping malformed question file %s: %s", file, exc)
        return None


def _read_topic(topic_dir: Path, topic: str) -> list[Question]:
    """Load every valid question in a topic folder, skipping malformed files."""
    questions: list[Question] = []
    for file in sorted(topic_dir.glob("*.json")):
        question = _read_question(file, topic)
        if question is not None:
            questions.append(question)
    return questions


def load_quiz(topic: str, base: Path = QUESTIONS_DIR) -> list[Question]:
    """Load all valid questions for a topic.

    Args:
        topic: Topic name, matching a folder under `base`.
        base: Corpus root directory. Defaults to the repo's questions/ dir.

    Returns:
        The topic's valid questions, with id (filename stem) and topic (folder
        name) derived from each file's path. Malformed files are skipped.

    Raises:
        TopicNotFoundError: If no folder exists for the topic.
    """
    topic_dir = base / topic
    if not topic_dir.is_dir():
        raise TopicNotFoundError(topic)
    return _read_topic(topic_dir, topic)


def list_topics(base: Path = QUESTIONS_DIR) -> list[Topic]:
    """Enumerate every topic folder under `base` with its valid-question count.

    Args:
        base: Corpus root directory. Defaults to the repo's questions/ dir.

    Returns:
        One Topic per subfolder, sorted by name, where count is the number of
        valid questions (malformed files are not counted).
    """
    if not base.is_dir():
        return []
    topics: list[Topic] = []
    for topic_dir in sorted(p for p in base.iterdir() if p.is_dir()):
        count = len(_read_topic(topic_dir, topic_dir.name))
        topics.append(Topic(topic=topic_dir.name, count=count))
    return topics
