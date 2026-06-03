"""Tests for quiz randomization and `count` semantics.

`select_questions` is pure, so it is driven directly with a controlled list of
Question objects. The /quiz route's `count` param is also exercised at the HTTP
boundary via TestClient against the real corpus. Randomness is asserted without
flakiness: orderings are checked as permutations/subsets, and the "is it
actually shuffled" check sweeps fixed seeds so the result is deterministic.
"""

import random

from fastapi.testclient import TestClient

from app.corpus import select_questions
from app.main import app
from app.models import Question

SHAPE = {"id", "topic", "question", "options", "correct"}


def make_pool(n: int, topic: str = "python") -> list[Question]:
    """Build n distinct, valid questions in the given topic."""
    return [
        Question(
            id=f"q{i}",
            topic=topic,
            question=f"Question {i}?",
            options=["a", "b"],
            correct=0,
        )
        for i in range(n)
    ]


def test_count_caps_result() -> None:
    pool = make_pool(5)
    result = select_questions(pool, count=2)
    assert len(result) == 2


def test_count_larger_than_pool_returns_all() -> None:
    pool = make_pool(3)
    result = select_questions(pool, count=99)
    assert len(result) == 3


def test_count_omitted_returns_all() -> None:
    pool = make_pool(4)
    result = select_questions(pool)
    assert len(result) == 4


def test_count_zero_returns_empty() -> None:
    assert select_questions(make_pool(4), count=0) == []


def test_count_negative_returns_empty() -> None:
    assert select_questions(make_pool(4), count=-1) == []


def test_no_duplicates() -> None:
    pool = make_pool(6)
    result = select_questions(pool, count=6)
    ids = [q.id for q in result]
    assert len(ids) == len(set(ids))


def test_result_is_permutation_of_full_pool() -> None:
    """All-questions case: returned set of ids equals the input set."""
    pool = make_pool(7)
    result = select_questions(pool)
    assert {q.id for q in result} == {q.id for q in pool}


def test_capped_result_is_subset_of_pool() -> None:
    """A capped draw returns distinct ids that all came from the pool."""
    pool = make_pool(10)
    pool_ids = {q.id for q in pool}
    result = select_questions(pool, count=4)
    result_ids = [q.id for q in result]
    assert set(result_ids) <= pool_ids
    assert len(result_ids) == len(set(result_ids))


def test_returned_questions_belong_to_pool_and_keep_shape() -> None:
    """Returned objects are the pool's own valid Questions, topic preserved."""
    pool = make_pool(5, topic="sql")
    result = select_questions(pool, count=5)
    for q in result:
        assert q.topic == "sql"
        assert q.model_dump().keys() >= SHAPE


def test_order_is_randomized_across_seeds() -> None:
    """Sweeping fixed seeds yields more than one ordering -> order is shuffled.

    Deterministic (seeds are fixed), and every ordering is a full permutation
    of the pool, so this never flakes.
    """
    pool = make_pool(8)
    expected_ids = {q.id for q in pool}
    orderings = set()
    for seed in range(20):
        random.seed(seed)
        result = select_questions(pool)
        assert {q.id for q in result} == expected_ids
        orderings.add(tuple(q.id for q in result))
    assert len(orderings) > 1


def test_http_count_caps_result() -> None:
    """The /quiz route honors `count` end-to-end (real corpus has >=2 python q)."""
    client = TestClient(app)

    full = client.get("/quiz", params={"topic": "python"})
    assert full.status_code == 200
    available = len(full.json())
    assert available >= 2

    capped = client.get("/quiz", params={"topic": "python", "count": 1})
    assert capped.status_code == 200
    body = capped.json()
    assert len(body) == 1
    assert body[0]["topic"] == "python"
    assert body[0].keys() >= SHAPE

    over = client.get("/quiz", params={"topic": "python", "count": 999})
    assert over.status_code == 200
    assert len(over.json()) == available
