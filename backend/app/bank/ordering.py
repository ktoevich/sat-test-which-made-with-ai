"""The order questions run in inside a module: easy first, hard last.

The reference tables in ``SAT test structure/`` give every module a difficulty
band per question number — module 1 runs 1-7 Easy, 8-15 Medium, 16-22 Hard.
The bank stores each module already in that order, so question 5 of a paper in
``answer-keys/`` is question 5 of the exam, and serving a module never has to
reshuffle it. Inside a band the questions keep the order they were drawn in,
which the assembler already mixes by topic; grid-ins sit wherever their
difficulty puts them, as on the real test.
"""

from __future__ import annotations

from typing import Any, Iterable, Mapping, Sequence

from .schema import MODULE_KEYS

Question = dict[str, Any]

#: Position of each bank difficulty inside a module.
DIFFICULTY_ORDER: Mapping[str, int] = {"Easy": 1, "Medium": 2, "Hard": 3}

#: Where a question with a missing or unknown difficulty goes.
DEFAULT_DIFFICULTY = "Medium"


def difficulty_rank(question: Mapping[str, Any]) -> int:
    difficulty = question.get("difficulty", DEFAULT_DIFFICULTY)
    return DIFFICULTY_ORDER.get(difficulty, DIFFICULTY_ORDER[DEFAULT_DIFFICULTY])


def exam_order(questions: Iterable[Question]) -> list[Question]:
    """``questions`` sorted into the exam's bands, stable inside each band."""
    return sorted(questions, key=difficulty_rank)


def is_exam_order(questions: Sequence[Mapping[str, Any]]) -> bool:
    ranks = [difficulty_rank(question) for question in questions]
    return all(earlier <= later for earlier, later in zip(ranks, ranks[1:]))


def order_bundle(bundle: dict[str, Any]) -> list[str]:
    """Put every module of ``bundle`` in exam order, in place.

    Returns the keys of the modules that had to move.
    """
    changed: list[str] = []
    for key in MODULE_KEYS:
        module = bundle.get(key)
        if not isinstance(module, list) or is_exam_order(module):
            continue
        bundle[key] = exam_order(module)
        changed.append(key)
    return changed


def order_bank(bank: Iterable[dict[str, Any]]) -> int:
    """Put every module of every bundle in exam order, in place.

    Returns how many modules had to move.
    """
    return sum(len(order_bundle(bundle)) for bundle in bank)
