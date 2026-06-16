"""Tests for the question writer: files land on disk and round-trip through corpus."""

import json
from pathlib import Path

from app.corpus import load_quiz
from app.generation.generation import QuestionDraft
from app.generation.writer import write_questions


def _draft(question: str, correct: int = 0) -> QuestionDraft:
    return QuestionDraft(
        question=question,
        options=["a", "b", "c", "d"],
        correct=correct,
        explanation="why",
    )


def test_writes_one_file_per_draft(tmp_path: Path) -> None:
    paths = write_questions(
        "REST API", [_draft("What is REST?"), _draft("What is HTTP?")], base=tmp_path
    )

    assert len(paths) == 2
    assert all(p.exists() and p.suffix == ".json" for p in paths)
    # Folder name is slugified; files hold only the four content fields.
    assert paths[0].parent == tmp_path / "rest-api"
    body = json.loads(paths[0].read_text())
    assert set(body) == {"question", "options", "correct", "explanation"}


def test_id_is_stable_content_hash_so_reruns_are_idempotent(tmp_path: Path) -> None:
    first = write_questions("Topic", [_draft("Same question?")], base=tmp_path)
    second = write_questions("Topic", [_draft("Same question?")], base=tmp_path)

    assert first == second
    assert len(list((tmp_path / "topic").glob("*.json"))) == 1


def test_writes_title_manifest_without_clobbering(tmp_path: Path) -> None:
    write_questions("Topic", [_draft("Q?")], title="My Topic", base=tmp_path)
    manifest = tmp_path / "topic" / "topic.json"
    assert json.loads(manifest.read_text())["title"] == "My Topic"

    # A second run must not overwrite a (possibly hand-edited) manifest.
    manifest.write_text(json.dumps({"title": "Edited"}))
    write_questions("Topic", [_draft("Q?")], title="My Topic", base=tmp_path)
    assert json.loads(manifest.read_text())["title"] == "Edited"


def test_written_questions_load_back_through_corpus(tmp_path: Path) -> None:
    write_questions(
        "Python", [_draft("What is a GIL?", correct=2)], title="Python", base=tmp_path
    )

    questions = load_quiz("python", base=tmp_path)

    assert len(questions) == 1
    assert questions[0].question == "What is a GIL?"
    assert questions[0].topic == "python"
    assert questions[0].correct == 2
