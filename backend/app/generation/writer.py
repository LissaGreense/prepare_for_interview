"""Write generated questions to the on-disk corpus.

Each draft becomes one `questions/<topic_slug>/<id>.json` file holding only the four
content fields (`id`/`topic` are derived from the path by `corpus`, never stored).
The id is a short content hash of the question text, so re-running the same scope
overwrites rather than duplicates — generation is idempotent.
"""

from __future__ import annotations

import hashlib
import json
import logging
import re
from pathlib import Path

from ..corpus import MANIFEST_NAME, QUESTIONS_DIR
from .generation import QuestionDraft

_log = logging.getLogger(__name__)

#: Length of the content-hash id. 8 hex chars (32 bits) is collision-safe at the
#: single-user, few-hundred-question scale this app runs at.
_ID_LEN = 8


def _slugify(text: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return slug or "topic"


def _question_id(draft: QuestionDraft) -> str:
    # Content address, not a security digest — sha1 is fine and fast here.
    digest = hashlib.sha1(draft.question.encode(), usedforsecurity=False)
    return digest.hexdigest()[:_ID_LEN]


def write_questions(
    topic_slug: str,
    drafts: list[QuestionDraft],
    *,
    title: str | None = None,
    base: Path | None = None,
) -> list[Path]:
    """Write `drafts` into `base/<slug>/`, one JSON file each. Returns written paths.

    Args:
        topic_slug: Topic folder name (slugified defensively).
        drafts: Validated question drafts to persist.
        title: Optional display title; written to `topic.json` if no manifest exists
            yet (never clobbers a manifest the user may have hand-edited).
        base: Corpus root. Resolved at call time to the repo's questions/ dir when
            omitted; tests pass a tmp dir.

    Returns:
        The paths written, in input order. Empty if `drafts` is empty.
    """
    base = base if base is not None else QUESTIONS_DIR
    slug = _slugify(topic_slug)
    topic_dir = base / slug
    topic_dir.mkdir(parents=True, exist_ok=True)

    manifest = topic_dir / MANIFEST_NAME
    if title and not manifest.exists():
        manifest.write_text(json.dumps({"title": title}, indent=2) + "\n")

    written: list[Path] = []
    for draft in drafts:
        path = topic_dir / f"{_question_id(draft)}.json"
        path.write_text(json.dumps(draft.model_dump(), indent=2) + "\n")
        written.append(path)
    _log.info("wrote %d question(s) to %s", len(written), topic_dir)
    return written
