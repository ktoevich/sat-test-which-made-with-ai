"""Turns a stored module into the list the frontend shows."""

from __future__ import annotations

from typing import Any, Iterable

from ..bank.ordering import exam_order

Question = dict[str, Any]


def build_module(questions: Iterable[Question]) -> list[Question]:
    """Number a module's questions from 1, in exam order.

    The bank stores every module easy first and hard last, which is what the
    difficulty bands of the blueprint ask for: with a 7 / 8 / 7 split,
    questions 1-7 are easy, 8-15 medium and 16-22 hard. Sorting again here is
    a stable no-op for such a module and a safety net for a bank that was not
    reordered. Nothing is shuffled: the paper in ``answer-keys/`` and the exam
    number the questions the same way.
    """
    ordered = exam_order(questions)
    for number, question in enumerate(ordered, start=1):
        question["id"] = number
    return ordered
