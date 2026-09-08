import random
from collections import Counter

import pytest

from app.bank import blueprint, schema, taxonomy
from app.bank.assembler import BundleSpec, Slot, default_spec
from app.bank.generator import GenerationError, generate_bank, generate_questions
from app.bank.templates import TEMPLATES, supports, templates_for


@pytest.mark.parametrize("template", TEMPLATES, ids=lambda template: template.key)
def test_every_template_builds_valid_questions(template):
    rng = random.Random(11)
    for qtype in template.types:
        for difficulty in template.difficulties:
            for _ in range(120):
                question = template.build(rng, qtype, difficulty)
                assert schema.validate_question(question, template.key) == []
                assert question["type"] == qtype
                assert question["difficulty"] == difficulty
                assert question["domain"] and question["skill"]
                assert question["rationale"]


@pytest.mark.parametrize("template", TEMPLATES, ids=lambda template: template.key)
def test_multiple_choice_answers_point_at_a_real_option(template):
    if "MCQ" not in template.types:
        pytest.skip("template has no multiple-choice form")

    rng = random.Random(3)
    for difficulty in template.difficulties:
        for _ in range(120):
            question = template.build(rng, "MCQ", difficulty)
            letters = [schema.option_letter(option) for option in question["options"]]
            assert len(set(letters)) == len(letters)
            assert question["answer"] in letters
            bodies = [option[3:] for option in question["options"]]
            assert len(set(bodies)) == len(bodies), "options must be distinct"


def test_every_type_and_difficulty_has_at_least_one_template():
    for qtype in ("MCQ", "SPR"):
        for difficulty in ("Easy", "Medium", "Hard"):
            assert templates_for(qtype, difficulty), f"nothing produces {difficulty} {qtype}"


def test_generate_questions_builds_one_question_per_slot_in_order():
    slots = [Slot.any("MCQ", "Easy")] * 5 + [Slot.any("SPR", "Hard")] * 3
    questions = generate_questions(slots, rng=random.Random(1))

    assert [(q["type"], q["difficulty"]) for q in questions] == [
        (slot.qtype, slot.difficulty) for slot in slots
    ]


def test_generate_questions_stays_on_topic():
    slots = [Slot(("Circles",), "MCQ", "Easy"), Slot(("Percentages", "Circles"), "SPR", "Medium")]
    questions = generate_questions(slots, rng=random.Random(1))

    assert questions[0]["skill"] == "Circles"
    assert questions[1]["skill"] == "Percentages"  # the only one of the two with grid-ins


def test_an_unfillable_slot_relaxes_difficulty_before_type():
    # Nothing builds a Hard grid-in about scatterplots, but a Medium MCQ exists.
    slot = Slot(("Two-variable data: models and scatterplots",), "SPR", "Hard")
    question = generate_questions([slot], rng=random.Random(1))[0]

    assert question["skill"] == slot.skills[0]
    assert question["type"] == "MCQ"
    assert question["difficulty"] == "Medium"


def test_generated_questions_are_unique():
    questions = generate_questions([Slot.any("MCQ", "Medium")] * 40, rng=random.Random(9))

    # Identity covers the figure and the options, not just the prompt: templates
    # like line_graph reuse one wording and vary only the picture.
    assert len({q["question_id"] for q in questions}) == 40


def test_a_reused_prompt_still_yields_distinct_questions():
    """The graph template asks one question over many different figures."""
    from app.bank.templates import BY_KEY

    template = BY_KEY["line_graph"]
    rng = random.Random(5)
    built = [template.build(rng, "MCQ", "Easy") for _ in range(30)]

    assert len({q["text"] for q in built}) == 1
    assert len({q["question_id"] for q in built}) > 10


def test_generation_fails_loudly_when_no_template_fits():
    with pytest.raises(GenerationError, match="no template"):
        generate_questions([Slot(("Knitting",), "MCQ", "Easy")], rng=random.Random(1))


def test_generated_bank_passes_validation():
    bank = generate_bank(bundles=2, spec=default_spec(size=8, spr_count=2), rng=random.Random(4))

    assert schema.validate_bank(bank) == []
    assert [bundle["test_id"] for bundle in bank] == ["sat-generated-01", "sat-generated-02"]
    for bundle in bank:
        assert len(bundle["module_1"]) == 8


def test_the_same_seed_produces_the_same_bank():
    spec = default_spec(size=6, spr_count=2)
    first = generate_bank(bundles=1, spec=spec, rng=random.Random(42))
    second = generate_bank(bundles=1, spec=spec, rng=random.Random(42))
    assert first == second


def test_module_2_higher_is_harder_than_module_2_lower():
    bank = generate_bank(bundles=1, spec=default_spec(size=12, spr_count=3), rng=random.Random(7))
    bundle = bank[0]

    def hard_count(key: str) -> int:
        return sum(1 for question in bundle[key] if question["difficulty"] == "Hard")

    assert hard_count("module_2_HIGHER") > hard_count("module_2_LOWER")


# --- blueprint conformance -------------------------------------------


@pytest.mark.parametrize("template", TEMPLATES, ids=lambda template: template.key)
def test_every_template_declares_a_blueprint_domain_and_skill(template):
    domain = taxonomy.BY_NAME.get(template.domain)
    assert domain is not None, f"{template.domain!r} is not a Digital SAT content domain"
    assert template.skill in domain.skills, (
        f"{template.skill!r} is not a published skill under {domain.name}"
    )


def test_every_blueprint_skill_has_a_template():
    covered = {template.skill for template in TEMPLATES}
    assert taxonomy.ALL_SKILLS - covered == set()


@pytest.mark.parametrize("module", blueprint.MODULES, ids=lambda module: module.key)
def test_generated_modules_follow_the_reference_tables(module):
    bank = generate_bank(bundles=3, spec=BundleSpec(), rng=random.Random(17))

    for bundle in bank:
        questions = bundle[module.key]
        assert len(questions) == 22
        assert Counter(q["type"] for q in questions) == {"MCQ": 17, "SPR": 5}
        assert Counter(q["difficulty"] for q in questions) == module.difficulty_counts()

        by_domain = Counter(q["domain"] for q in questions)
        by_skill = Counter(q["skill"] for q in questions)
        for section in module.sections:
            assert section.minimum <= by_domain[section.domain] <= section.maximum, section.domain
            for topic in section.topics:
                count = sum(by_skill[skill] for skill in topic.skills)
                assert topic.minimum <= count <= topic.maximum, f"{module.key}: {topic.label}"


def test_the_templates_cover_every_planned_slot():
    """The plan never has to fall back, so bands and topics come out exact."""
    spec = BundleSpec()
    for seed in range(10):
        plan = spec.plan(random.Random(seed), supports)
        for key, slots in plan.items():
            for slot in slots:
                assert supports(slot.skills, slot.qtype, slot.difficulty), (key, slot)


def test_target_counts_add_up():
    for total in (44, 66, 100, 330):
        assert sum(taxonomy.target_counts(total).values()) == total
