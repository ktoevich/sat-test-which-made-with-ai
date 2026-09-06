"""Turns a raw list of bank questions into an ordered exam module."""

from __future__ import annotations

import random
from typing import Any, Iterable

Question = dict[str, Any]

#: Order in which difficulties are presented inside a module.
DIFFICULTY_ORDER = {"Easy": 1, "Medium": 2, "Hard": 3}
DEFAULT_DIFFICULTY = "Medium"

#: Question formats, in the order the digital SAT presents them.
QUESTION_TYPE_ORDER = ("MCQ", "SPR")


def _difficulty_rank(question: Question) -> int:
    return DIFFICULTY_ORDER.get(question.get("difficulty", DEFAULT_DIFFICULTY), 2)


def build_module(
    questions: Iterable[Question], *, rng: random.Random | None = None
) -> list[Question]:
    """Group questions by type, shuffle inside a group, then sort by difficulty.

    The shuffle keeps two attempts from looking identical; the stable sort that
    follows still guarantees ``Easy -> Medium -> Hard`` inside each group.
    Questions are renumbered from 1 so the frontend can rely on ``id``.
    """
    rng = rng or random
    pool = list(questions)

    ordered: list[Question] = []
    for question_type in QUESTION_TYPE_ORDER:
        group = [q for q in pool if q.get("type") == question_type]
        rng.shuffle(group)
        group.sort(key=_difficulty_rank)
        ordered.extend(group)

    # Anything with an unexpected type still gets served, just at the end.
    known = set(QUESTION_TYPE_ORDER)
    ordered.extend(q for q in pool if q.get("type") not in known)

    for number, question in enumerate(ordered, start=1):
        question["id"] = number

    return ordered
