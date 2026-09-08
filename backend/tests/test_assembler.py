import random
from collections import Counter

import pytest

from app.bank import blueprint
from app.bank.assembler import (
    AssemblyError,
    BundleSpec,
    ModuleSpec,
    QuestionPool,
    Slot,
    assemble_bank,
    default_spec,
)
from tests.conftest import make_question


def pool_of(counts: dict[tuple[str, str], int], skill: str | None = None) -> list[dict]:
    questions = []
    for (qtype, difficulty), amount in counts.items():
        for index in range(amount):
            question = make_question(f"{qtype}-{difficulty}-{index}", qtype, difficulty)
            if skill:
                question["skill"] = skill
            questions.append(question)
    return questions


def test_module_requirements_split_by_the_bands():
    spec = ModuleSpec(blueprint.MODULE_1)
    requirements = spec.requirements()

    assert sum(requirements.values()) == 22
    assert sum(count for (qtype, _), count in requirements.items() if qtype == "SPR") == 5
    assert sum(count for (qtype, _), count in requirements.items() if qtype == "MCQ") == 17
    by_difficulty = Counter()
    for (_, difficulty), count in requirements.items():
        by_difficulty[difficulty] += count
    assert by_difficulty == {"Easy": 7, "Medium": 8, "Hard": 7}


def test_requirements_always_add_up_to_the_module_size():
    for size in range(5, 30):
        spec = ModuleSpec(blueprint.MODULE_1.scaled(size, size // 4))
        assert sum(spec.requirements().values()) == size


def test_bundle_requirements_cover_all_three_modules():
    spec = default_spec(size=10, spr_count=2)
    assert sum(spec.requirements().values()) == 30
    assert spec.size == 30


def test_the_default_spec_is_three_full_modules():
    spec = BundleSpec()
    assert spec.size == 66
    for module in spec.modules().values():
        assert (module.size, module.mcq_count, module.spr_count) == (22, 17, 5)


def test_a_plan_has_one_slot_per_question_and_respects_the_bands():
    spec = ModuleSpec(blueprint.MODULE_2_LOWER)
    slots = spec.plan(random.Random(3))

    assert len(slots) == 22
    assert Counter(slot.qtype for slot in slots) == {"MCQ": 17, "SPR": 5}
    assert Counter(slot.difficulty for slot in slots) == {"Easy": 10, "Medium": 8, "Hard": 4}
    assert all(slot.skills for slot in slots)


def test_a_plan_avoids_combinations_nothing_can_fill():
    def only_mcq_for_circles(skills, qtype, difficulty):
        return "Circles" not in skills or qtype == "MCQ"

    slots = ModuleSpec(blueprint.MODULE_1).plan(random.Random(1), only_mcq_for_circles)
    assert all(slot.qtype == "MCQ" for slot in slots if "Circles" in slot.skills)


def test_a_plan_is_still_produced_when_nothing_fits():
    slots = ModuleSpec(blueprint.MODULE_1).plan(random.Random(1), lambda *_: False)
    assert len(slots) == 22


def test_pool_draws_without_repeats():
    pool = QuestionPool(pool_of({("MCQ", "Easy"): 5}), random.Random(1))
    first = pool.draw(Slot.any("MCQ", "Easy"), 3)
    second = pool.draw(Slot.any("MCQ", "Easy"), 2)

    ids = [q["question_id"] for q in first + second]
    assert len(set(ids)) == 5
    assert pool.available("MCQ", "Easy") == 0


def test_pool_prefers_questions_on_topic():
    on_topic = pool_of({("MCQ", "Easy"): 1}, skill="Circles")
    off_topic = pool_of({("MCQ", "Easy"): 3}, skill="Percentages")
    pool = QuestionPool(off_topic + on_topic, random.Random(1))

    drawn = pool.draw(Slot(("Circles",), "MCQ", "Easy"))
    assert drawn[0]["skill"] == "Circles"


def test_pool_prefers_on_topic_over_exact_difficulty():
    questions = pool_of({("MCQ", "Easy"): 2}, skill="Percentages") + pool_of(
        {("MCQ", "Hard"): 1}, skill="Circles"
    )
    pool = QuestionPool(questions, random.Random(1))

    drawn = pool.draw(Slot(("Circles",), "MCQ", "Easy"))
    assert drawn[0]["skill"] == "Circles"
    assert drawn[0]["difficulty"] == "Hard"


def test_pool_falls_back_to_any_topic_as_a_last_resort():
    pool = QuestionPool(pool_of({("MCQ", "Easy"): 1}, skill="Percentages"), random.Random(1))
    assert pool.draw(Slot(("Circles",), "MCQ", "Easy"))[0]["skill"] == "Percentages"


def test_unlabelled_questions_fit_any_slot():
    pool = QuestionPool(pool_of({("MCQ", "Easy"): 1}), random.Random(1))
    assert pool.supports(("Circles",), "MCQ", "Easy")
    assert pool.draw(Slot(("Circles",), "MCQ", "Easy"))


def test_pool_falls_back_to_a_neighbouring_difficulty():
    pool = QuestionPool(pool_of({("MCQ", "Medium"): 2}), random.Random(1))
    drawn = pool.draw(Slot.any("MCQ", "Easy"), 2)
    assert [q["difficulty"] for q in drawn] == ["Medium", "Medium"]


def test_pool_falls_back_to_the_other_type_as_a_last_resort():
    pool = QuestionPool(pool_of({("SPR", "Easy"): 1}), random.Random(1))
    assert pool.draw(Slot.any("MCQ", "Easy"))[0]["type"] == "SPR"


def test_pool_reports_what_it_could_not_fill():
    pool = QuestionPool(pool_of({("MCQ", "Easy"): 1}), random.Random(1))
    with pytest.raises(AssemblyError, match="ran out"):
        pool.draw(Slot.any("MCQ", "Easy"), 3)


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
            assert sum(1 for q in bundle[key] if q["type"] == "SPR") == 2


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
