import random

from app.services import build_module
from tests.conftest import make_question


def test_groups_by_type_then_sorts_by_difficulty():
    questions = [
        make_question("spr-hard", "SPR", "Hard"),
        make_question("mcq-hard", "MCQ", "Hard"),
        make_question("spr-easy", "SPR", "Easy"),
        make_question("mcq-easy", "MCQ", "Easy"),
    ]

    ordered = build_module(questions, rng=random.Random(0))

    assert [q["question_id"] for q in ordered] == [
        "mcq-easy",
        "mcq-hard",
        "spr-easy",
        "spr-hard",
    ]


def test_renumbers_ids_from_one():
    questions = [make_question(f"q{i}", "MCQ", "Easy") for i in range(3)]
    assert [q["id"] for q in build_module(questions)] == [1, 2, 3]


def test_questions_with_unknown_type_are_kept_last():
    questions = [
        {"question_id": "weird", "type": "ESSAY", "difficulty": "Easy"},
        make_question("mcq", "MCQ", "Easy"),
    ]
    ordered = build_module(questions)
    assert [q["question_id"] for q in ordered] == ["mcq", "weird"]


def test_missing_difficulty_falls_back_to_medium():
    questions = [
        {"question_id": "hard", "type": "MCQ", "difficulty": "Hard"},
        {"question_id": "unknown", "type": "MCQ"},
        {"question_id": "easy", "type": "MCQ", "difficulty": "Easy"},
    ]
    ordered = build_module(questions)
    assert [q["question_id"] for q in ordered] == ["easy", "unknown", "hard"]
