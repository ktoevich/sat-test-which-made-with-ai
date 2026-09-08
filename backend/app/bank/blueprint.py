"""The module structure of this mock test, transcribed from ``SAT test structure/``.

The folder at the repository root holds the reference tables: for each module a
difficulty band per question number, and for each content domain the subtopics
it draws from and how many questions each contributes. This module encodes those
tables so the assembler and the generator build modules that follow them.

Every module has :data:`QUESTIONS_PER_MODULE` questions, of which
:data:`MULTIPLE_CHOICE_PER_MODULE` are multiple choice and
:data:`STUDENT_RESPONSE_PER_MODULE` are grid-ins. Module 1 is the same for
everyone; the second module is the easier route below
:data:`ADAPTIVE_MIN_CORRECT` correct answers in module 1 and the harder route at
or above it.

The bank labels difficulty as Easy, Medium or Hard, so the harder route's
"Medium Hard" and "Very Hard" bands both draw from the Hard pool.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass, replace
from typing import Iterator

from . import taxonomy

QUESTIONS_PER_MODULE = 22
MULTIPLE_CHOICE_PER_MODULE = 17
STUDENT_RESPONSE_PER_MODULE = QUESTIONS_PER_MODULE - MULTIPLE_CHOICE_PER_MODULE

#: Correct answers in module 1 (out of :data:`QUESTIONS_PER_MODULE`) needed for
#: the harder module 2.
ADAPTIVE_MIN_CORRECT = 15


class BlueprintError(ValueError):
    """Raised when a blueprint cannot be turned into a module of the right size."""


@dataclass(frozen=True)
class Band:
    """A run of question numbers sharing one difficulty."""

    label: str
    #: The bank difficulty questions in this band are drawn from.
    difficulty: str
    first: int
    last: int

    @property
    def count(self) -> int:
        return self.last - self.first + 1


@dataclass(frozen=True)
class Topic:
    """A subtopic row: which blueprint skills it covers and how many questions."""

    label: str
    note: str
    skills: tuple[str, ...]
    minimum: int
    maximum: int


@dataclass(frozen=True)
class Section:
    """A content domain and the number of questions it gets in the module."""

    domain: str
    minimum: int
    maximum: int
    topics: tuple[Topic, ...]


@dataclass(frozen=True)
class ModuleBlueprint:
    key: str
    title: str
    description: str
    bands: tuple[Band, ...]
    sections: tuple[Section, ...]
    size: int = QUESTIONS_PER_MODULE
    spr_count: int = STUDENT_RESPONSE_PER_MODULE

    @property
    def mcq_count(self) -> int:
        return self.size - self.spr_count

    def difficulty_counts(self) -> dict[str, int]:
        """Questions per bank difficulty, in band order."""
        counts: dict[str, int] = {}
        for band in self.bands:
            counts[band.difficulty] = counts.get(band.difficulty, 0) + band.count
        return counts

    def topics(self) -> Iterator[tuple[Section, Topic]]:
        for section in self.sections:
            for topic in section.topics:
                yield section, topic

    def skills(self) -> frozenset[str]:
        return frozenset(skill for _, topic in self.topics() for skill in topic.skills)

    # -- sizing ------------------------------------------------------------

    def scaled(self, size: int, spr_count: int) -> "ModuleBlueprint":
        """The same structure shrunk or grown to ``size`` questions.

        Used for small test banks and the ``--module-size`` flag. Ranges are
        scaled proportionally, rounding minimums down and maximums up, so the
        result is always fillable.
        """
        if size == self.size and spr_count == self.spr_count:
            return self
        if size <= 0 or not 0 <= spr_count <= size:
            raise BlueprintError(f"cannot build a {size}-question module with {spr_count} grid-ins")

        ratio = size / self.size

        def low(value: int) -> int:
            return math.floor(value * ratio)

        def high(value: int) -> int:
            return math.ceil(value * ratio)

        sections = tuple(
            replace(
                section,
                minimum=low(section.minimum),
                maximum=high(section.maximum),
                topics=tuple(
                    replace(topic, minimum=low(topic.minimum), maximum=high(topic.maximum))
                    for topic in section.topics
                ),
            )
            for section in self.sections
        )

        shares = {band: band.count for band in self.bands}
        counts = _largest_remainder(shares, size)
        bands: list[Band] = []
        position = 1
        for band in self.bands:
            count = counts[band]
            if not count:
                continue
            bands.append(replace(band, first=position, last=position + count - 1))
            position += count

        return replace(self, bands=tuple(bands), sections=sections, size=size, spr_count=spr_count)

    # -- resolution --------------------------------------------------------

    def resolve_topics(self, rng: random.Random) -> dict[Topic, int]:
        """Pick an exact question count per topic inside the blueprint's ranges.

        Starts from every minimum, tops sections up to their own minimum, then
        hands out the remaining questions at random to topics with headroom in
        sections that are not full yet.
        """
        counts = {topic: topic.minimum for _, topic in self.topics()}

        def total(section: Section) -> int:
            return sum(counts[topic] for topic in section.topics)

        def open_topics(section: Section) -> list[Topic]:
            return [topic for topic in section.topics if counts[topic] < topic.maximum]

        for section in self.sections:
            while total(section) < section.minimum:
                options = open_topics(section)
                if not options:
                    raise BlueprintError(
                        f"{self.key}: {section.domain} needs {section.minimum} questions "
                        f"but its topics allow at most {total(section)}"
                    )
                counts[rng.choice(options)] += 1

        remaining = self.size - sum(counts.values())
        if remaining < 0:
            raise BlueprintError(
                f"{self.key}: topic minimums add up to more than {self.size} questions"
            )

        for _ in range(remaining):
            options = [
                topic
                for section in self.sections
                if total(section) < section.maximum
                for topic in open_topics(section)
            ]
            if not options:
                raise BlueprintError(
                    f"{self.key}: topic maximums add up to fewer than {self.size} questions"
                )
            counts[rng.choice(options)] += 1

        return counts


def _largest_remainder(shares: dict, total: int) -> dict:
    """Split ``total`` proportionally to ``shares``; leftovers go to the largest fractions."""
    weight = sum(shares.values()) or 1
    exact = {key: total * share / weight for key, share in shares.items()}
    counts = {key: int(value) for key, value in exact.items()}
    remainder = total - sum(counts.values())
    for key in sorted(exact, key=lambda key: exact[key] - counts[key], reverse=True)[:remainder]:
        counts[key] += 1
    return counts


def check(blueprint: ModuleBlueprint) -> list[str]:
    """Every way a blueprint could be inconsistent; empty means it is sound."""
    problems: list[str] = []
    prefix = blueprint.key

    expected = 1
    for band in blueprint.bands:
        if band.first != expected:
            problems.append(f"{prefix}: band {band.label!r} starts at {band.first}, expected {expected}")
        if band.difficulty not in taxonomy.DIFFICULTIES:
            problems.append(f"{prefix}: band {band.label!r} uses unknown difficulty {band.difficulty!r}")
        expected = band.last + 1
    if expected - 1 != blueprint.size:
        problems.append(f"{prefix}: bands cover {expected - 1} questions, module has {blueprint.size}")

    if not 0 <= blueprint.spr_count <= blueprint.size:
        problems.append(f"{prefix}: {blueprint.spr_count} grid-ins do not fit in {blueprint.size} questions")

    floor = 0
    ceiling = 0
    for section in blueprint.sections:
        if section.domain not in taxonomy.BY_NAME:
            problems.append(f"{prefix}: {section.domain!r} is not a content domain")
        topic_floor = sum(topic.minimum for topic in section.topics)
        topic_ceiling = sum(topic.maximum for topic in section.topics)
        if topic_floor > section.maximum:
            problems.append(f"{prefix}: {section.domain} topic minimums exceed the section maximum")
        if topic_ceiling < section.minimum:
            problems.append(f"{prefix}: {section.domain} topic maximums cannot reach the section minimum")
        for topic in section.topics:
            if topic.minimum > topic.maximum:
                problems.append(f"{prefix}: {topic.label!r} has minimum above maximum")
            for skill in topic.skills:
                domain = taxonomy.domain_of(skill)
                if domain is None:
                    problems.append(f"{prefix}: {topic.label!r} names unknown skill {skill!r}")
                elif domain.name != section.domain:
                    problems.append(f"{prefix}: {skill!r} belongs to {domain.name}, not {section.domain}")
        floor += max(section.minimum, topic_floor)
        ceiling += min(section.maximum, topic_ceiling)

    if floor > blueprint.size:
        problems.append(f"{prefix}: section minimums add up to {floor}, more than {blueprint.size}")
    if ceiling < blueprint.size:
        problems.append(f"{prefix}: section maximums add up to {ceiling}, fewer than {blueprint.size}")
    return problems


# -- the tables from ``SAT test structure/`` -------------------------------

_ALGEBRA = taxonomy.ALGEBRA.name
_ADVANCED = taxonomy.ADVANCED_MATH.name
_DATA = taxonomy.PROBLEM_SOLVING.name
_GEOMETRY = taxonomy.GEOMETRY.name

LINEAR_ONE = "Linear equations in one variable"
LINEAR_TWO = "Linear equations in two variables"
LINEAR_FUNCTIONS = "Linear functions"
SYSTEMS = "Systems of two linear equations in two variables"
INEQUALITIES = "Linear inequalities in one or two variables"
EQUIVALENT = "Equivalent expressions"
NONLINEAR_EQUATIONS = "Nonlinear equations in one variable and systems of equations in two variables"
NONLINEAR_FUNCTIONS = "Nonlinear functions"
RATIOS = "Ratios, rates, proportional relationships, and units"
PERCENTAGES = "Percentages"
ONE_VARIABLE = "One-variable data: distributions and measures of center and spread"
TWO_VARIABLE = "Two-variable data: models and scatterplots"
PROBABILITY = "Probability and conditional probability"
MARGIN_OF_ERROR = "Inference from sample statistics and margin of error"
CLAIMS = "Evaluating statistical claims: observational studies and experiments"
AREA_VOLUME = "Area and volume"
LINES_ANGLES = "Lines, angles, and triangles"
RIGHT_TRIANGLES = "Right triangles and trigonometry"
CIRCLES = "Circles"


MODULE_1 = ModuleBlueprint(
    key="module_1",
    title="Module 1",
    description=(
        "Everyone starts here. The number of correct answers decides which "
        "module 2 follows."
    ),
    bands=(
        Band("Easy", "Easy", 1, 7),
        Band("Medium", "Medium", 8, 15),
        Band("Hard", "Hard", 16, 22),
    ),
    sections=(
        Section(_ALGEBRA, 7, 8, (
            Topic("Linear functions", "basic linear graphs and functions", (LINEAR_FUNCTIONS,), 2, 3),
            Topic("Linear equations in two variables", "equations in x and y", (LINEAR_TWO,), 2, 2),
            Topic("Linear equations in one variable", "linear equations in x", (LINEAR_ONE,), 1, 2),
            Topic("Systems of two linear equations", "basic systems", (SYSTEMS,), 1, 1),
            Topic("Linear inequalities", "simple inequalities", (INEQUALITIES,), 1, 1),
        )),
        Section(_ADVANCED, 7, 8, (
            Topic("Nonlinear functions", "parabolas and exponentials", (NONLINEAR_FUNCTIONS,), 2, 3),
            Topic("Nonlinear equations and systems", "quadratic equations", (NONLINEAR_EQUATIONS,), 2, 3),
            Topic("Equivalent expressions", "expanding brackets, exponents", (EQUIVALENT,), 2, 2),
        )),
        Section(_DATA, 3, 4, (
            Topic("Ratios, rates, and units", "ratios, rates, unit conversion", (RATIOS,), 1, 2),
            Topic("Percentages", "percentages", (PERCENTAGES,), 1, 1),
            Topic("1-variable / 2-variable data", "basic graphs and statistics", (ONE_VARIABLE, TWO_VARIABLE), 1, 1),
        )),
        Section(_GEOMETRY, 3, 4, (
            Topic("Area and volume", "basic areas and volumes", (AREA_VOLUME,), 1, 1),
            Topic("Lines, angles, and triangles", "angles and lines", (LINES_ANGLES,), 1, 1),
            Topic("Right triangles and trigonometry", "Pythagorean theorem, sin / cos", (RIGHT_TRIANGLES,), 1, 1),
            Topic("Circles", "simple circles", (CIRCLES,), 0, 1),
        )),
    ),
)

MODULE_2_LOWER = ModuleBlueprint(
    key="module_2_LOWER",
    title="Module 2 — Lower",
    description=(
        f"The easier route, served after fewer than {ADAPTIVE_MIN_CORRECT} of "
        f"{QUESTIONS_PER_MODULE} correct answers in module 1."
    ),
    bands=(
        Band("Easy", "Easy", 1, 10),
        Band("Medium", "Medium", 11, 18),
        Band("Hard", "Hard", 19, 22),
    ),
    sections=(
        Section(_ALGEBRA, 8, 9, (
            Topic("Linear functions", "simple graphs: find the slope or an intercept", (LINEAR_FUNCTIONS,), 3, 3),
            Topic("Linear equations in one variable", "equations in one variable", (LINEAR_ONE,), 2, 3),
            Topic("Linear inequalities", "linear inequalities", (INEQUALITIES,), 1, 2),
            Topic("Linear equations / Systems", "basic equations in two variables", (LINEAR_TWO, SYSTEMS), 1, 2),
        )),
        Section(_ADVANCED, 4, 6, (
            Topic("Equivalent expressions", "basic algebraic manipulation", (EQUIVALENT,), 2, 3),
            Topic("Nonlinear functions", "substituting numbers into a given formula", (NONLINEAR_FUNCTIONS,), 1, 2),
            Topic("Nonlinear equations", "simple quadratic equations", (NONLINEAR_EQUATIONS,), 1, 1),
        )),
        Section(_DATA, 4, 5, (
            Topic("Percentages", "discounts, taxes, tips", (PERCENTAGES,), 2, 2),
            Topic("Ratios, rates, and units", "simple conversions", (RATIOS,), 1, 2),
            Topic("1-variable / 2-variable data", "reading bar charts", (ONE_VARIABLE, TWO_VARIABLE), 1, 1),
        )),
        Section(_GEOMETRY, 3, 4, (
            Topic("Area and volume", "calculations for basic shapes", (AREA_VOLUME,), 1, 2),
            Topic("Lines, angles, and triangles", "adjacent and vertical angles", (LINES_ANGLES,), 1, 2),
            Topic("Right triangles and trigonometry", "Pythagorean theorem", (RIGHT_TRIANGLES,), 0, 1),
            Topic("Circles", "almost never appears", (CIRCLES,), 0, 0),
        )),
    ),
)

MODULE_2_HIGHER = ModuleBlueprint(
    key="module_2_HIGHER",
    title="Module 2 — Higher",
    description=(
        f"The harder route, served after {ADAPTIVE_MIN_CORRECT} or more of "
        f"{QUESTIONS_PER_MODULE} correct answers in module 1."
    ),
    bands=(
        Band("Medium", "Medium", 1, 5),
        Band("Medium Hard", "Hard", 6, 15),
        Band("Very Hard", "Hard", 16, 22),
    ),
    sections=(
        Section(_ADVANCED, 9, 10, (
            Topic("Nonlinear functions", "harder parabolas, graph shifts", (NONLINEAR_FUNCTIONS,), 3, 4),
            Topic("Nonlinear equations & systems", "discriminant, intersections", (NONLINEAR_EQUATIONS,), 3, 4),
            Topic("Equivalent expressions", "complex fractions, exponents and roots", (EQUIVALENT,), 2, 2),
        )),
        Section(_ALGEBRA, 5, 6, (
            Topic("Systems of two linear equations", "systems with constants: no solutions / infinitely many", (SYSTEMS,), 2, 3),
            Topic("Linear equations in two variables", "convoluted word problems", (LINEAR_TWO,), 2, 3),
            Topic("Linear equations / Inequalities", "rare", (LINEAR_ONE, INEQUALITIES), 0, 1),
        )),
        Section(_GEOMETRY, 3, 4, (
            Topic("Circles", "long equations x² + y² + …, radians", (CIRCLES,), 1, 2),
            Topic("Right triangles and trigonometry", "sin(x) = cos(90° − x), similarity", (RIGHT_TRIANGLES,), 1, 1),
            Topic("Area and volume", "scaling problems (k and k³)", (AREA_VOLUME,), 1, 1),
            Topic("Lines, angles, and triangles", "rare", (LINES_ANGLES,), 0, 1),
        )),
        Section(_DATA, 2, 3, (
            Topic("Evaluating claims & Margin of error", "statistical conclusions", (CLAIMS, MARGIN_OF_ERROR), 1, 2),
            Topic("Probability", "harder probability", (PROBABILITY,), 1, 1),
            Topic("Percentages / Ratios", "very rare", (PERCENTAGES, RATIOS), 0, 1),
        )),
    ),
)

MODULES: tuple[ModuleBlueprint, ...] = (MODULE_1, MODULE_2_HIGHER, MODULE_2_LOWER)
BY_KEY: dict[str, ModuleBlueprint] = {module.key: module for module in MODULES}
