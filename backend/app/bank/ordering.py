"""The order questions run in inside a module.

A math module runs easy first and hard last: the reference tables in ``SAT test
structure/`` give it a difficulty band per question number — module 1 runs 1-7
Easy, 8-15 Medium, 16-22 Hard. A Reading and Writing module is grouped by
domain instead, in the order the real test presents them — Craft and
Structure, Information and Ideas, Expression of Ideas, Standard English
Conventions — and runs easy to hard inside each group.

The bank stores each module already in its order, so question 5 of a paper in
``answer-keys/`` is question 5 of the exam, and serving a module never has to
reshuffle it. Inside a band the questions keep the order they were drawn in,
which the assembler already mixes by topic; grid-ins sit wherever their
difficulty puts them, as on the real test.
"""

from __future__ import annotations

from typing import Any, Callable, Iterable, Mapping, Sequence

from . import taxonomy
from .schema import MODULE_KEYS

Question = dict[str, Any]

#: Position of each bank difficulty inside a module.
DIFFICULTY_ORDER: Mapping[str, int] = {"Easy": 1, "Medium": 2, "Hard": 3}

#: Where a question with a missing or unknown difficulty goes.
DEFAULT_DIFFICULTY = "Medium"

#: Position of each Reading and Writing domain inside a module.
DOMAIN_ORDER: Mapping[str, int] = {
    domain.name: position for position, domain in enumerate(taxonomy.READING_DOMAINS)
}


def difficulty_rank(question: Mapping[str, Any]) -> int:
    difficulty = question.get("difficulty", DEFAULT_DIFFICULTY)
    return DIFFICULTY_ORDER.get(difficulty, DIFFICULTY_ORDER[DEFAULT_DIFFICULTY])


def domain_rank(question: Mapping[str, Any]) -> int:
    """Unknown or unlabelled domains go after the known ones."""
    return DOMAIN_ORDER.get(question.get("domain") or "", len(DOMAIN_ORDER))


def sort_key(section: str | None = None) -> Callable[[Mapping[str, Any]], tuple]:
    """The key a module of ``section`` is sorted by."""
    if taxonomy.section_of(section).ordering == "domain":
        return lambda question: (domain_rank(question), difficulty_rank(question))
    return lambda question: (difficulty_rank(question),)


def exam_order(questions: Iterable[Question], section: str | None = None) -> list[Question]:
    """``questions`` sorted into the exam's order for ``section``, stable inside each group."""
    return sorted(questions, key=sort_key(section))


def is_exam_order(questions: Sequence[Mapping[str, Any]], section: str | None = None) -> bool:
    key = sort_key(section)
    ranks = [key(question) for question in questions]
    return all(earlier <= later for earlier, later in zip(ranks, ranks[1:]))


def bundle_section(bundle: Mapping[str, Any]) -> str:
    """The section a bundle belongs to; a bundle that does not say is a math one."""
    return str(bundle.get("section") or taxonomy.DEFAULT_SECTION)


def order_bundle(bundle: dict[str, Any]) -> list[str]:
    """Put every module of ``bundle`` in exam order, in place.

    Returns the keys of the modules that had to move.
    """
    section = bundle_section(bundle)
    changed: list[str] = []
    for key in MODULE_KEYS:
        module = bundle.get(key)
        if not isinstance(module, list) or is_exam_order(module, section):
            continue
        bundle[key] = exam_order(module, section)
        changed.append(key)
    return changed


def order_bank(bank: Iterable[dict[str, Any]]) -> int:
    """Put every module of every bundle in exam order, in place.

    Returns how many modules had to move.
    """
    return sum(len(order_bundle(bundle)) for bundle in bank)
