"""The figures themselves, and which blueprint topics are guaranteed one.

Template-to-skill coverage is checked in test_blueprint.py; this file checks the
other half of the same promise — that the topics whose reference row asks for a
picture can actually be served one, and that the pictures are well formed.
"""

import random
import xml.etree.ElementTree as ElementTree

import pytest

from app.bank import blueprint, figures
from app.bank.templates import TEMPLATES, templates_for

#: Topics whose row in ``SAT test structure/`` describes a figure — "basic
#: linear graphs", "reading bar charts", "adjacent and vertical angles" — plus
#: the geometry and data rows that carry one on the real test. Keyed by the
#: skills the topic draws from, since that is what the generator matches on.
TOPICS_NEEDING_A_FIGURE = {
    "Linear functions",
    "One-variable data: distributions and measures of center and spread",
    "Two-variable data: models and scatterplots",
    "Lines, angles, and triangles",
    "Right triangles and trigonometry",
    "Area and volume",
    "Nonlinear functions",
}


def _draws_a_figure(template) -> bool:
    """Whether the template ever attaches an image, over a fair sample."""
    rng = random.Random(5)
    for qtype in template.types:
        for difficulty in template.difficulties:
            for _ in range(40):
                if template.build(rng, qtype, difficulty).get("image"):
                    return True
    return False


ILLUSTRATED = {template.key for template in TEMPLATES if _draws_a_figure(template)}


@pytest.mark.parametrize("skill", sorted(TOPICS_NEEDING_A_FIGURE))
def test_every_skill_that_needs_a_figure_has_a_template_that_draws_one(skill):
    drawing = [
        template.key
        for template in templates_for("MCQ", "Easy", (skill,)) + templates_for("MCQ", "Hard", (skill,))
        if template.key in ILLUSTRATED
    ]
    assert drawing, f"no template draws a figure for {skill!r}"


@pytest.mark.parametrize(
    "module_topic",
    [(module.key, topic) for module in blueprint.MODULES for _, topic in module.topics()],
    ids=lambda pair: f"{pair[0]}:{pair[1].label}" if isinstance(pair, tuple) else str(pair),
)
def test_illustrated_topics_can_be_filled_with_an_illustrated_question(module_topic):
    _, topic = module_topic
    if not TOPICS_NEEDING_A_FIGURE & set(topic.skills):
        pytest.skip("this topic is not one the reference tables illustrate")
    if topic.maximum == 0:
        pytest.skip("the reference table gives this topic no questions")

    candidates = {
        template.key
        for difficulty in ("Easy", "Medium", "Hard")
        for qtype in ("MCQ", "SPR")
        for template in templates_for(qtype, difficulty, topic.skills)
    }
    assert candidates & ILLUSTRATED, f"{topic.label} can never be served a figure"


@pytest.mark.parametrize("template", TEMPLATES, ids=lambda template: template.key)
def test_standalone_figures_are_well_formed_and_described(template):
    """Any SVG a template ships must parse and carry an ``aria-label``.

    The label is what a screen reader announces and what the Markdown export
    prints in place of the drawing, so a figure without one is a question that
    cannot be answered away from the browser.
    """
    rng = random.Random(17)
    for qtype in template.types:
        for difficulty in template.difficulties:
            for _ in range(30):
                image = template.build(rng, qtype, difficulty).get("image")
                if not isinstance(image, str):
                    continue
                root = ElementTree.fromstring(image)
                assert root.tag.endswith("svg")
                label = root.get("aria-label")
                assert label and len(label) > 20, f"{template.key}: figure is not described"
                assert figures.label_of(image) == label


def test_coordinate_grid_descriptors_stay_inside_their_grid():
    """A grid figure that draws outside its own bounds is clipped in the browser."""
    rng = random.Random(23)
    for template in TEMPLATES:
        for qtype in template.types:
            for difficulty in template.difficulties:
                for _ in range(40):
                    image = template.build(rng, qtype, difficulty).get("image")
                    if not isinstance(image, dict):
                        continue
                    assert image["xEnd"] > 0 and image["yEnd"] > 0
                    # Same contract as an SVG's aria-label: a grid figure has
                    # to say what is drawn on it, or the exported paper and a
                    # screen reader both lose the question.
                    assert len(image.get("alt", "")) > 20, (
                        f"{template.key}: grid figure is not described"
                    )
                    for name in ("x1", "y1", "x2", "y2", "cx", "cy"):
                        for value in _attribute_values(image["draw"], name):
                            limit = image["xEnd"] if name in ("x1", "x2", "cx") else image["yEnd"]
                            assert abs(value) <= limit + 1e-6, (
                                f"{template.key}: {name}={value} leaves the grid"
                            )


def _attribute_values(markup: str, name: str) -> list[float]:
    values = []
    needle = f'{name}="'
    start = markup.find(needle)
    while start >= 0:
        end = markup.find('"', start + len(needle))
        values.append(float(markup[start + len(needle) : end]))
        start = markup.find(needle, end)
    return values


def test_bar_chart_axis_covers_the_tallest_bar():
    top, step = figures._axis_scale(23)
    assert top >= 23 and top % step == 0


def test_a_figure_label_survives_a_round_trip():
    markup = figures.svg("", width=10, height=10, label='A "quoted" & escaped label')
    assert figures.label_of(markup) == 'A "quoted" & escaped label'
