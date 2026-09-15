"""The Digital SAT blueprint: the two sections, their domains and skills.

These are the published structural facts about the test — how long a module is,
how many questions it holds, and the names of the content domains and the skills
under each. Templates declare which of these they cover, and the generator uses
the domain shares to balance a bank.

The math section came first and its constants are module-level; the Reading
and Writing section is described the same way through :class:`Section`, and
:data:`SECTIONS` lists both.

Source: College Board's SAT Suite specifications
(https://satsuite.collegeboard.org/k12-educators/about/alignment/math,
https://satsuite.collegeboard.org/k12-educators/about/alignment/reading-writing
and https://satsuite.collegeboard.org/sat/whats-on-the-test/structure).
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

#: The math content domains, in the order College Board lists them.
DOMAINS: tuple[Domain, ...] = (ALGEBRA, ADVANCED_MATH, PROBLEM_SOLVING, GEOMETRY)

#: Domain name -> share of the math section.
DOMAIN_SHARES: dict[str, float] = {domain.name: domain.share for domain in DOMAINS}

#: Every math skill name in the blueprint.
ALL_SKILLS: frozenset[str] = frozenset(
    skill for domain in DOMAINS for skill in domain.skills
)


# -- Reading and Writing -------------------------------------------------

CRAFT_AND_STRUCTURE = Domain(
    key="craft_and_structure",
    name="Craft and Structure",
    share=0.28,
    skills=(
        "Words in Context",
        "Text Structure and Purpose",
        "Cross-Text Connections",
    ),
)

INFORMATION_AND_IDEAS = Domain(
    key="information_and_ideas",
    name="Information and Ideas",
    share=0.26,
    skills=(
        "Central Ideas and Details",
        "Command of Evidence",
        "Inferences",
    ),
)

EXPRESSION_OF_IDEAS = Domain(
    key="expression_of_ideas",
    name="Expression of Ideas",
    share=0.20,
    skills=(
        "Rhetorical Synthesis",
        "Transitions",
    ),
)

STANDARD_ENGLISH_CONVENTIONS = Domain(
    key="standard_english_conventions",
    name="Standard English Conventions",
    share=0.26,
    skills=(
        "Boundaries",
        "Form, Structure, and Sense",
    ),
)

#: The Reading and Writing domains, in the order a module presents them.
READING_DOMAINS: tuple[Domain, ...] = (
    CRAFT_AND_STRUCTURE,
    INFORMATION_AND_IDEAS,
    EXPRESSION_OF_IDEAS,
    STANDARD_ENGLISH_CONVENTIONS,
)


# -- The two sections ----------------------------------------------------


@dataclass(frozen=True)
class Section:
    """One of the test's two sections and how its modules are built."""

    key: str
    name: str
    minutes_per_module: int
    questions_per_module: int
    multiple_choice_per_module: int
    #: Correct answers in module 1 that lead to the harder module 2.
    adaptive_min_correct: int
    domains: tuple[Domain, ...]
    #: How a module is ordered: ``"difficulty"`` runs easy to hard;
    #: ``"domain"`` groups the questions by domain, easy to hard inside each.
    ordering: str

    @property
    def student_response_per_module(self) -> int:
        return self.questions_per_module - self.multiple_choice_per_module

    def skills(self) -> frozenset[str]:
        return frozenset(skill for domain in self.domains for skill in domain.skills)


MATH = Section(
    key="math",
    name="Math",
    minutes_per_module=MINUTES_PER_MODULE,
    questions_per_module=QUESTIONS_PER_MODULE,
    multiple_choice_per_module=MULTIPLE_CHOICE_PER_MODULE,
    adaptive_min_correct=15,
    domains=DOMAINS,
    ordering="difficulty",
)

#: Reading and Writing: two modules of 27 multiple-choice questions, 32 minutes
#: each, every question a short passage with one question about it. The
#: questions come grouped by domain, in :data:`READING_DOMAINS` order, and run
#: easy to hard inside each group.
READING = Section(
    key="reading",
    name="Reading and Writing",
    minutes_per_module=32,
    questions_per_module=27,
    multiple_choice_per_module=27,
    adaptive_min_correct=18,
    domains=READING_DOMAINS,
    ordering="domain",
)

SECTIONS: tuple[Section, ...] = (MATH, READING)
SECTION_BY_KEY: dict[str, Section] = {section.key: section for section in SECTIONS}
SECTION_KEYS: tuple[str, ...] = tuple(section.key for section in SECTIONS)
#: Banks and requests that do not say which section they mean are math ones:
#: that is what the app served before it had a second section.
DEFAULT_SECTION = MATH.key

#: Every domain of both sections.
ALL_DOMAINS: tuple[Domain, ...] = DOMAINS + READING_DOMAINS

BY_NAME: dict[str, Domain] = {domain.name: domain for domain in ALL_DOMAINS}


def section_of(key: str | None) -> Section:
    """The section for a key, the default section for a missing one."""
    return SECTION_BY_KEY[key or DEFAULT_SECTION]


def section_of_domain(name: str) -> Section | None:
    return next((section for section in SECTIONS if name in {d.name for d in section.domains}), None)


def domain_of(skill: str) -> Domain | None:
    """Find the domain a skill belongs to, in either section."""
    return next((domain for domain in ALL_DOMAINS if skill in domain.skills), None)


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
