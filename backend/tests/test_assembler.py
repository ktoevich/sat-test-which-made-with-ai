import random

import pytest

from app.bank.assembler import (
    MODULE_1_MIX,
    AssemblyError,
    BundleSpec,
    ModuleSpec,
    QuestionPool,
    assemble_bank,
    default_spec,
)
from tests.conftest import make_question


def pool_of(counts: dict[tuple[str, str], int]) -> list[dict]:
    questions = []
    for (qtype, difficulty), amount in counts.items():
        for index in range(amount):
            questions.append(make_question(f"{qtype}-{difficulty}-{index}", qtype, difficulty))
    return questions


def test_module_requirements_split_by_the_mix():
    spec = ModuleSpec(MODULE_1_MIX, size=20, spr_count=4)
    requirements = spec.requirements()

    assert sum(requirements.values()) == 20
    assert sum(count for (qtype, _), count in requirements.items() if qtype == "SPR") == 4
    assert sum(count for (qtype, _), count in requirements.items() if qtype == "MCQ") == 16


def test_requirements_always_add_up_to_the_module_size():
    for size in range(5, 30):
        spec = ModuleSpec(MODULE_1_MIX, size=size, spr_count=size // 4)
        assert sum(spec.requirements().values()) == size


def test_bundle_requirements_cover_all_three_modules():
    spec = default_spec(size=10, spr_count=2)
    assert sum(spec.requirements().values()) == 30


def test_pool_draws_without_repeats():
    pool = QuestionPool(pool_of({("MCQ", "Easy"): 5}), random.Random(1))
    first = pool.draw("MCQ", "Easy", 3)
    second = pool.draw("MCQ", "Easy", 2)

    ids = [q["question_id"] for q in first + second]
    assert len(set(ids)) == 5
    assert pool.available("MCQ", "Easy") == 0


def test_pool_falls_back_to_a_neighbouring_difficulty():
    pool = QuestionPool(pool_of({("MCQ", "Medium"): 2}), random.Random(1))
    drawn = pool.draw("MCQ", "Easy", 2)
    assert [q["difficulty"] for q in drawn] == ["Medium", "Medium"]


def test_pool_falls_back_to_the_other_type_as_a_last_resort():
    pool = QuestionPool(pool_of({("SPR", "Easy"): 1}), random.Random(1))
    assert pool.draw("MCQ", "Easy", 1)[0]["type"] == "SPR"


def test_pool_reports_what_it_could_not_fill():
    pool = QuestionPool(pool_of({("MCQ", "Easy"): 1}), random.Random(1))
    with pytest.raises(AssemblyError, match="ran out"):
        pool.draw("MCQ", "Easy", 3)


def test_assemble_bank_builds_modules_of_the_requested_size():
    spec = default_spec(size=6, spr_count=2)
    questions = pool_of(
        {
            ("MCQ", "Easy"): 10,
            ("MCQ", "Medium"): 10,
            ("MCQ", "Hard"): 10,
            ("SPR", "Easy"): 5,
            ("SPR", "Medium"): 5,
            ("SPR", "Hard"): 5,
        }
    )

    bundles = assemble_bank(questions, bundles=2, spec=spec, rng=random.Random(5))

    assert [bundle["test_id"] for bundle in bundles] == ["sat-mock-01", "sat-mock-02"]
    for bundle in bundles:
        for key in ("module_1", "module_2_HIGHER", "module_2_LOWER"):
            assert len(bundle[key]) == 6


def test_module_2_variants_skew_in_opposite_directions():
    spec = BundleSpec()
    higher = spec.module_2_higher.requirements()
    lower = spec.module_2_lower.requirements()

    hard_in_higher = sum(count for (_, level), count in higher.items() if level == "Hard")
    hard_in_lower = sum(count for (_, level), count in lower.items() if level == "Hard")
    assert hard_in_higher > hard_in_lower


def test_bundles_hold_independent_copies():
    spec = default_spec(size=3, spr_count=1)
    questions = pool_of({("MCQ", "Easy"): 20, ("MCQ", "Hard"): 20, ("SPR", "Easy"): 20})
    bundles = assemble_bank(questions, bundles=1, spec=spec, rng=random.Random(2))

    bundles[0]["module_1"][0]["text"] = "mutated"
    assert all(question["text"] != "mutated" for question in questions)


def test_a_pool_that_is_too_small_is_rejected_up_front():
    with pytest.raises(AssemblyError, match="need"):
        assemble_bank(pool_of({("MCQ", "Easy"): 3}), bundles=1, spec=default_spec(size=6, spr_count=2))
