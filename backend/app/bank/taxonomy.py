"""The Digital SAT Math blueprint: section structure, domains and skills.

These are the published structural facts about the test — how long a module is,
how many questions it holds, and the names of the content domains and the skills
under each. Templates declare which of these they cover, and the generator uses
the domain shares to balance a bank.

Source: College Board's SAT Suite specifications
(https://satsuite.collegeboard.org/k12-educators/about/alignment/math and
https://satsuite.collegeboard.org/sat/whats-on-the-test/structure).
"""

from __future__ import annotations

from dataclasses import dataclass

# -- Section structure -------------------------------------------------

#: The math section is two adaptive modules.
MODULE_COUNT = 2
#: Minutes allowed per module.
MINUTES_PER_MODULE = 35
#: Questions shown per module.
QUESTIONS_PER_MODULE = 22
#: Questions across the whole section, a few of which are unscored pretest items.
TOTAL_QUESTIONS = MODULE_COUNT * QUESTIONS_PER_MODULE

#: Each module is 17 multiple-choice questions and 5 student-produced responses
#: (grid-ins). Where each of them falls is laid out in :mod:`.blueprint`.
MULTIPLE_CHOICE_PER_MODULE = 17
STUDENT_RESPONSE_PER_MODULE = QUESTIONS_PER_MODULE - MULTIPLE_CHOICE_PER_MODULE

#: The difficulty labels the bank uses, easiest first.
DIFFICULTIES = ("Easy", "Medium", "Hard")


@dataclass(frozen=True)
class Domain:
    """One content domain and the skills tested under it."""

    key: str
    name: str
    #: Approximate share of the math section, as published.
    share: float
    skills: tuple[str, ...]


ALGEBRA = Domain(
    key="algebra",
    name="Algebra",
    share=0.35,
    skills=(
        "Linear equations in one variable",
        "Linear equations in two variables",
        "Linear functions",
        "Systems of two linear equations in two variables",
        "Linear inequalities in one or two variables",
    ),
)

ADVANCED_MATH = Domain(
    key="advanced_math",
    name="Advanced Math",
    share=0.35,
    skills=(
        "Equivalent expressions",
        "Nonlinear equations in one variable and systems of equations in two variables",
        "Nonlinear functions",
    ),
)

PROBLEM_SOLVING = Domain(
    key="problem_solving",
    name="Problem-Solving and Data Analysis",
    share=0.15,
    skills=(
        "Ratios, rates, proportional relationships, and units",
        "Percentages",
        "One-variable data: distributions and measures of center and spread",
        "Two-variable data: models and scatterplots",
        "Probability and conditional probability",
        "Inference from sample statistics and margin of error",
        "Evaluating statistical claims: observational studies and experiments",
    ),
)

GEOMETRY = Domain(
    key="geometry",
    name="Geometry and Trigonometry",
    share=0.15,
    skills=(
        "Area and volume",
        "Lines, angles, and triangles",
        "Right triangles and trigonometry",
        "Circles",
    ),
)

DOMAINS: tuple[Domain, ...] = (ALGEBRA, ADVANCED_MATH, PROBLEM_SOLVING, GEOMETRY)

BY_NAME: dict[str, Domain] = {domain.name: domain for domain in DOMAINS}

#: Domain name -> share of the section.
DOMAIN_SHARES: dict[str, float] = {domain.name: domain.share for domain in DOMAINS}

#: Every skill name in the blueprint.
ALL_SKILLS: frozenset[str] = frozenset(
    skill for domain in DOMAINS for skill in domain.skills
)


def domain_of(skill: str) -> Domain | None:
    """Find the domain a skill belongs to."""
    return next((domain for domain in DOMAINS if skill in domain.skills), None)


def target_counts(total: int) -> dict[str, int]:
    """Split ``total`` questions across the domains by their published shares.

    Leftovers from rounding go to the domains with the largest fractional part,
    so the counts always add up to ``total``.
    """
    if total <= 0:
        return {domain.name: 0 for domain in DOMAINS}

    exact = {domain.name: total * domain.share for domain in DOMAINS}
    counts = {name: int(value) for name, value in exact.items()}

    remainder = total - sum(counts.values())
    by_fraction = sorted(exact, key=lambda name: exact[name] - counts[name], reverse=True)
    for name in by_fraction[:remainder]:
        counts[name] += 1
    return counts
