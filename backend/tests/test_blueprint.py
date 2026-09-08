import random
from collections import Counter

import pytest

from app.bank import blueprint, taxonomy
from app.bank.blueprint import Band, BlueprintError, ModuleBlueprint, Section, Topic
from app.bank.templates import TEMPLATES


@pytest.mark.parametrize("module", blueprint.MODULES, ids=lambda module: module.key)
def test_every_module_is_internally_consistent(module):
    assert blueprint.check(module) == []


@pytest.mark.parametrize("module", blueprint.MODULES, ids=lambda module: module.key)
def test_every_module_is_22_questions_with_17_multiple_choice_and_5_grid_ins(module):
    assert module.size == 22
    assert module.mcq_count == 17
    assert module.spr_count == 5
    assert sum(band.count for band in module.bands) == 22


def test_module_1_bands_follow_the_reference_table():
    assert [(b.first, b.last, b.label) for b in blueprint.MODULE_1.bands] == [
        (1, 7, "Easy"),
        (8, 15, "Medium"),
        (16, 22, "Hard"),
    ]


def test_module_2_lower_bands_follow_the_reference_table():
    assert [(b.first, b.last, b.label) for b in blueprint.MODULE_2_LOWER.bands] == [
        (1, 10, "Easy"),
        (11, 18, "Medium"),
        (19, 22, "Hard"),
    ]


def test_module_2_higher_bands_follow_the_reference_table():
    bands = blueprint.MODULE_2_HIGHER.bands
    assert [(b.first, b.last, b.label) for b in bands] == [
        (1, 5, "Medium"),
        (6, 15, "Medium Hard"),
        (16, 22, "Very Hard"),
    ]
    # The bank has three difficulty labels, so both harder bands draw from Hard.
    assert blueprint.MODULE_2_HIGHER.difficulty_counts() == {"Medium": 5, "Hard": 17}


def test_the_harder_route_needs_15_of_22():
    assert blueprint.ADAPTIVE_MIN_CORRECT == 15


@pytest.mark.parametrize("module", blueprint.MODULES, ids=lambda module: module.key)
def test_every_topic_names_blueprint_skills_of_its_own_domain(module):
    for section, topic in module.topics():
        for skill in topic.skills:
            assert taxonomy.domain_of(skill).name == section.domain


@pytest.mark.parametrize("module", blueprint.MODULES, ids=lambda module: module.key)
def test_every_topic_with_questions_has_a_template(module):
    covered = {template.skill for template in TEMPLATES}
    for _, topic in module.topics():
        if topic.maximum:
            assert set(topic.skills) & covered, f"{module.key}: nothing builds {topic.label!r}"


@pytest.mark.parametrize("module", blueprint.MODULES, ids=lambda module: module.key)
def test_resolved_topics_stay_inside_their_ranges_and_add_up(module):
    for seed in range(25):
        counts = module.resolve_topics(random.Random(seed))
        assert sum(counts.values()) == module.size
        for section in module.sections:
            total = sum(counts[topic] for topic in section.topics)
            assert section.minimum <= total <= section.maximum, section.domain
            for topic in section.topics:
                assert topic.minimum <= counts[topic] <= topic.maximum, topic.label


def test_resolution_varies_between_draws():
    seen = {tuple(sorted(blueprint.MODULE_1.resolve_topics(random.Random(seed)).values())) for seed in range(20)}
    assert len(seen) > 1


def test_scaling_keeps_the_structure_fillable():
    for size in range(3, 30):
        scaled = blueprint.MODULE_1.scaled(size, size // 4)
        assert scaled.size == size
        assert scaled.spr_count == size // 4
        assert blueprint.check(scaled) == []
        assert sum(scaled.resolve_topics(random.Random(size)).values()) == size


def test_scaling_to_the_native_size_is_a_no_op():
    assert blueprint.MODULE_1.scaled(22, 5) is blueprint.MODULE_1


def test_scaled_bands_keep_their_order_and_cover_the_module():
    scaled = blueprint.MODULE_2_HIGHER.scaled(11, 3)
    assert scaled.bands[0].first == 1
    assert scaled.bands[-1].last == 11
    assert [band.label for band in scaled.bands] == ["Medium", "Medium Hard", "Very Hard"]


def test_an_impossible_blueprint_is_reported():
    broken = ModuleBlueprint(
        key="broken",
        title="Broken",
        description="",
        bands=(Band("Easy", "Easy", 1, 4),),
        sections=(
            Section("Algebra", 4, 4, (Topic("Lines", "", ("Linear functions",), 1, 2),)),
        ),
        size=4,
        spr_count=1,
    )
    assert any("topic maximums" in problem for problem in blueprint.check(broken))
    with pytest.raises(BlueprintError):
        broken.resolve_topics(random.Random(0))


def test_check_flags_unknown_skills_and_gaps_in_the_bands():
    broken = ModuleBlueprint(
        key="broken",
        title="Broken",
        description="",
        bands=(Band("Easy", "Easy", 2, 4),),
        sections=(
            Section("Algebra", 0, 3, (Topic("Made up", "", ("Knitting",), 0, 3),)),
        ),
        size=3,
        spr_count=1,
    )
    problems = "\n".join(blueprint.check(broken))
    assert "Knitting" in problems
    assert "expected 1" in problems


def test_section_ranges_reflect_the_reference_tables():
    def ranges(module):
        return {section.domain: (section.minimum, section.maximum) for section in module.sections}

    assert ranges(blueprint.MODULE_1) == {
        "Algebra": (7, 8),
        "Advanced Math": (7, 8),
        "Problem-Solving and Data Analysis": (3, 4),
        "Geometry and Trigonometry": (3, 4),
    }
    assert ranges(blueprint.MODULE_2_LOWER)["Algebra"] == (8, 9)
    assert ranges(blueprint.MODULE_2_HIGHER)["Advanced Math"] == (9, 10)
    assert Counter(section.domain for section in blueprint.MODULE_2_HIGHER.sections) == Counter(
        domain.name for domain in taxonomy.DOMAINS
    )
