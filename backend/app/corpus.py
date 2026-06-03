"""Read quiz questions from disk.

The filesystem is the source of truth: each topic is a folder under the
questions directory, and each question is one JSON file whose stem is the
question id. Files are read per request (no startup cache) so newly added
files appear immediately.
"""

import json
from pathlib import Path

from .models import Question

# Single swappable place for the corpus root. Resolved relative to this source
# file (app -> backend -> repo root) so it does not depend on the process CWD.
# A later task can point the loader at a fixture directory by passing `base`.
QUESTIONS_DIR = Path(__file__).resolve().parents[2] / "questions"


class TopicNotFoundError(Exception):
    """Raised when a requested topic has no corresponding folder on disk."""


def load_quiz(topic: str, base: Path = QUESTIONS_DIR) -> list[Question]:
    """Load all questions for a topic.

    Args:
        topic: Topic name, matching a folder under `base`.
        base: Corpus root directory. Defaults to the repo's questions/ dir.

    Returns:
        The topic's questions, with id (filename stem) and topic (folder name)
        derived from each file's path.

    Raises:
        TopicNotFoundError: If no folder exists for the topic.
    """
    topic_dir = base / topic
    if not topic_dir.is_dir():
        raise TopicNotFoundError(topic)

    questions: list[Question] = []
    for file in sorted(topic_dir.glob("*.json")):
        data = json.loads(file.read_text())
        questions.append(Question(id=file.stem, topic=topic, **data))
    return questions
