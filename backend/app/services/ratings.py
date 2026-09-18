"""The rating a student carries between attempts, Codeforces-style.

Every finished test moves the rating by an amount that depends on the score
alone: a 600 leaves it where it was, an 800 adds 90, a 400 takes 90 away.
The rating is one number across both sections — a strong Reading and Writing
score lifts it as much as a strong maths one — and never drops below the
floor, so a run of bad days does not dig a hole nobody climbs out of.

The tier is not read off the rating. It is the band of the student's best
score in either section, on the test's own 200-800 scale: Basic, then
Intermediate from 500, Advanced from 600 and Elite from 700.
"""

from __future__ import annotations

START_RATING = 1200
FLOOR = 800
CEILING = 2400

#: The score that leaves the rating unchanged, and the points per score point.
NEUTRAL_SCORE = 600
POINTS_PER_SCORE_POINT = 0.45

#: Tiers by the SAT score they start at, highest first.
TIERS: tuple[tuple[int, str], ...] = (
    (700, "elite"),
    (600, "advanced"),
    (500, "intermediate"),
    (0, "basic"),
)


def tier(best_score: int | None) -> str:
    """The tier of a best score; a student with no test yet is Basic."""
    value = 0 if best_score is None else int(best_score)
    return next(name for floor, name in TIERS if value >= floor)


def delta(score: int) -> int:
    """How much a score moves the rating."""
    return round((int(score) - NEUTRAL_SCORE) * POINTS_PER_SCORE_POINT)


def apply(rating: int | None, score: int) -> int:
    """The rating after a test scored ``score``."""
    current = START_RATING if rating is None else int(rating)
    return max(FLOOR, min(CEILING, current + delta(score)))
