import random

from app.services import build_module
from tests.conftest import make_question


def test_sorts_by_difficulty_with_grid_ins_in_the_mix():
    questions = [
        make_question("spr-hard", "SPR", "Hard"),
        make_question("mcq-hard", "MCQ", "Hard"),
        make_question("spr-easy", "SPR", "Easy"),
        make_question("mcq-easy", "MCQ", "Easy"),
        make_question("mcq-medium", "MCQ", "Medium"),
    ]

    ordered = build_module(questions, rng=random.Random(0))

    assert [q["difficulty"] for q in ordered] == ["Easy", "Easy", "Medium", "Hard", "Hard"]
    assert {q["question_id"] for q in ordered[:2]} == {"spr-easy", "mcq-easy"}
    assert {q["question_id"] for q in ordered[-2:]} == {"spr-hard", "mcq-hard"}


def test_a_full_module_lands_in_the_blueprint_bands():
    questions = (
        [make_question(f"h{i}", "MCQ", "Hard") for i in range(7)]
        + [make_question(f"e{i}", "SPR" if i < 2 else "MCQ", "Easy") for i in range(7)]
        + [make_question(f"m{i}", "MCQ", "Medium") for i in range(8)]
    )

    ordered = build_module(questions, rng=random.Random(1))

    assert [q["id"] for q in ordered] == list(range(1, 23))
    assert all(q["difficulty"] == "Easy" for q in ordered[0:7])
    assert all(q["difficulty"] == "Medium" for q in ordered[7:15])
    assert all(q["difficulty"] == "Hard" for q in ordered[15:22])


def test_the_order_inside_a_band_varies_between_attempts():
    questions = [make_question(f"q{i}", "MCQ", "Easy") for i in range(8)]
    orders = {
        tuple(q["question_id"] for q in build_module(list(questions), rng=random.Random(seed)))
        for seed in range(10)
    }
    assert len(orders) > 1


def test_renumbers_ids_from_one():
    questions = [make_question(f"q{i}", "MCQ", "Easy") for i in range(3)]
    assert [q["id"] for q in build_module(questions)] == [1, 2, 3]


def test_missing_difficulty_falls_back_to_medium():
    questions = [
        {"question_id": "hard", "type": "MCQ", "difficulty": "Hard"},
        {"question_id": "unknown", "type": "MCQ"},
        {"question_id": "easy", "type": "MCQ", "difficulty": "Easy"},
    ]
    ordered = build_module(questions)
    assert [q["question_id"] for q in ordered] == ["easy", "unknown", "hard"]
