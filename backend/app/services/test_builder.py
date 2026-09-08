"""Turns a raw list of bank questions into an ordered exam module."""

from __future__ import annotations

import random
from typing import Any, Iterable

Question = dict[str, Any]

#: Order in which difficulties are presented inside a module.
DIFFICULTY_ORDER = {"Easy": 1, "Medium": 2, "Hard": 3}
DEFAULT_DIFFICULTY = "Medium"


def _difficulty_rank(question: Question) -> int:
    return DIFFICULTY_ORDER.get(question.get("difficulty", DEFAULT_DIFFICULTY), 2)


def build_module(
    questions: Iterable[Question], *, rng: random.Random | None = None
) -> list[Question]:
    """Shuffle, then sort by difficulty so the module runs ``Easy -> Medium -> Hard``.

    That reproduces the difficulty bands of the blueprint: with a 7 / 8 / 7
    split, questions 1-7 are easy, 8-15 medium and 16-22 hard. Grid-ins are not
    grouped at the end; like on the real test they sit wherever their difficulty
    puts them. The shuffle keeps two attempts from looking identical, and the
    stable sort that follows preserves the bands.

    Questions are renumbered from 1 so the frontend can rely on ``id``.
    """
    rng = rng or random
    ordered = list(questions)
    rng.shuffle(ordered)
    ordered.sort(key=_difficulty_rank)

    for number, question in enumerate(ordered, start=1):
        question["id"] = number

    return ordered
