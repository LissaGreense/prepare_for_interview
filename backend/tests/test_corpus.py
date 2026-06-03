"""Tests for the corpus reader and the topic/quiz endpoints.

The filesystem is the boundary worth exercising, so these tests write real
fixture files into a temp dir and point the reader at it via the `base` seam.
"""

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.corpus import TopicNotFoundError, list_topics, load_quiz
from app.main import app

VALID = {
    "question": "What does CPython's GIL protect?",
    "options": ["refcounts", "the filesystem", "GPU memory", "sockets"],
    "correct": 0,
    "explanation": "It serializes access to interpreter state.",
}


def _write(path: Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(payload if isinstance(payload, str) else json.dumps(payload))


def test_load_quiz_skips_malformed_keeps_siblings(tmp_path: Path) -> None:
    _write(tmp_path / "python" / "good.json", VALID)
    _write(tmp_path / "python" / "bad_json.json", "{not valid json")
    _write(tmp_path / "python" / "out_of_range.json", {**VALID, "correct": 9})
    _write(tmp_path / "python" / "wrong_schema.json", {"question": "no options"})

    questions = load_quiz("python", base=tmp_path)

    assert [q.id for q in questions] == ["good"]
    assert questions[0].topic == "python"


def test_load_quiz_unknown_topic_raises(tmp_path: Path) -> None:
    with pytest.raises(TopicNotFoundError):
        load_quiz("nope", base=tmp_path)


def test_list_topics_counts_only_valid(tmp_path: Path) -> None:
    _write(tmp_path / "python" / "a.json", VALID)
    _write(tmp_path / "python" / "b.json", VALID)
    _write(tmp_path / "python" / "bad.json", "{nope")
    _write(tmp_path / "sql" / "a.json", VALID)
    _write(tmp_path / "empty" / "all_bad.json", {**VALID, "correct": 99})

    topics = list_topics(base=tmp_path)

    # No manifests present: title falls back to the folder name, icon/description None.
    assert [t.model_dump() for t in topics] == [
        {
            "topic": "empty",
            "title": "empty",
            "icon": None,
            "description": None,
            "count": 0,
        },
        {
            "topic": "python",
            "title": "python",
            "icon": None,
            "description": None,
            "count": 2,
        },
        {"topic": "sql", "title": "sql", "icon": None, "description": None, "count": 1},
    ]


def test_list_topics_missing_base_is_empty(tmp_path: Path) -> None:
    assert list_topics(base=tmp_path / "does-not-exist") == []


def test_topic_manifest_is_read_and_not_counted(tmp_path: Path) -> None:
    _write(tmp_path / "python" / "a.json", VALID)
    _write(tmp_path / "python" / "b.json", VALID)
    _write(
        tmp_path / "python" / "topic.json",
        {"title": "Python", "icon": "🐍", "description": "Core language."},
    )

    (topic,) = list_topics(base=tmp_path)

    assert topic.title == "Python"
    assert topic.icon == "🐍"
    assert topic.description == "Core language."
    assert topic.count == 2  # the manifest itself is not counted as a question


def test_load_quiz_ignores_manifest(tmp_path: Path) -> None:
    _write(tmp_path / "python" / "a.json", VALID)
    _write(tmp_path / "python" / "topic.json", {"title": "Python"})

    questions = load_quiz("python", base=tmp_path)

    assert [q.id for q in questions] == ["a"]


def test_malformed_manifest_falls_back_to_folder_name(tmp_path: Path) -> None:
    _write(tmp_path / "python" / "a.json", VALID)
    _write(tmp_path / "python" / "topic.json", "{not valid json")

    (topic,) = list_topics(base=tmp_path)

    assert topic.title == "python"
    assert topic.icon is None
    assert topic.count == 1


def test_endpoints_against_real_corpus() -> None:
    """Smoke-test the wired app. The question bank lives in a gitignored,
    local-only `questions/` dir, so this asserts shape and behavior without
    assuming any specific topic exists (the fixture-based tests above carry
    the real coverage)."""
    client = TestClient(app)

    topics = client.get("/topics")
    assert topics.status_code == 200
    payload = topics.json()
    assert isinstance(payload, list)
    for t in payload:
        assert t.keys() >= {"topic", "title", "count"}

    # If any topic exists locally, a quiz for it returns the documented shape.
    if payload:
        quiz = client.get("/quiz", params={"topic": payload[0]["topic"]})
        assert quiz.status_code == 200
        if quiz.json():
            first = quiz.json()[0]
            assert first.keys() >= {"id", "topic", "question", "options", "correct"}

    # An unknown topic is always a 404, regardless of local content.
    assert client.get("/quiz", params={"topic": "no-such-topic"}).status_code == 404
