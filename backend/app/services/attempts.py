"""Finished test attempts, stored per user."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Mapping

from ..bank.taxonomy import DEFAULT_SECTION, SECTION_KEYS
from ..db import Database
from . import accounts, ratings

#: Cap on the stored per-question breakdown, so one attempt cannot bloat the DB.
MAX_DETAIL_QUESTIONS = 200
#: A module is 35 minutes; two of them plus a break is the most a test can take.
MAX_TIME_SPENT = 3 * 60 * 60


def _row_to_dict(row: Mapping[str, Any]) -> dict[str, Any]:
    try:
        details = json.loads(row["details"])
    except (json.JSONDecodeError, TypeError):
        details = []
    return {
        **summary_row(row),
        "details": details,
    }


def summary_row(row: Mapping[str, Any]) -> dict[str, Any]:
    """An attempt without its per-question breakdown: what a list shows."""
    return {
        "id": int(row["id"]),
        "taken_at": row["taken_at"],
        "section": row["section"] or DEFAULT_SECTION,
        "score": row["score"],
        "correct": row["correct"],
        "total": row["total"],
        "test_id": row["test_id"] or "",
        "target": row["target"] or "",
        "time_spent": int(row["time_spent"] or 0),
        "rating_before": row["rating_before"],
        "rating_after": row["rating_after"],
    }


def record(
    db: Database,
    *,
    user_id: int,
    score: int,
    correct: int,
    total: int,
    details: list[dict[str, Any]] | None = None,
    section: str = DEFAULT_SECTION,
    test_id: str = "",
    target: str = "",
    time_spent: int = 0,
) -> dict[str, Any]:
    """Save one finished attempt of one section, move the rating, and return it.

    ``test_id`` is the bank test it was, so it can be retaken; ``target`` the
    module 2 route it got; ``time_spent`` the seconds it took.
    """
    trimmed = (details or [])[:MAX_DETAIL_QUESTIONS]
    user = accounts.get_user(db, user_id)
    rating_after = ratings.apply(user.rating, int(score))
    attempt_id = db.insert(
        """
        INSERT INTO attempts (
            user_id, taken_at, section, score, correct, total, details,
            test_id, target, time_spent, rating_before, rating_after
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            user_id,
            datetime.now(timezone.utc).isoformat(timespec="seconds"),
            section,
            int(score),
            int(correct),
            int(total),
            json.dumps(trimmed, ensure_ascii=False),
            str(test_id or "")[:80],
            str(target or "")[:16].upper(),
            max(0, min(MAX_TIME_SPENT, int(time_spent or 0))),
            user.rating,
            rating_after,
        ),
    )
    accounts.record_rating(db, user_id, rating_after)
    db.commit()
    return get(db, user_id, attempt_id)


def list_for_user(db: Database, user_id: int, *, limit: int = 50) -> list[dict[str, Any]]:
    """A user's attempts, newest first."""
    rows = db.fetch_all(
        "SELECT * FROM attempts WHERE user_id = ? ORDER BY taken_at DESC, id DESC LIMIT ?",
        (user_id, limit),
    )
    return [_row_to_dict(row) for row in rows]


def list_summaries(db: Database, user_id: int, *, limit: int = 50) -> list[dict[str, Any]]:
    """A user's attempts without their breakdowns, newest first — the public view."""
    rows = db.fetch_all(
        """
        SELECT id, user_id, taken_at, section, score, correct, total, test_id, target,
               time_spent, rating_before, rating_after
        FROM attempts WHERE user_id = ? ORDER BY taken_at DESC, id DESC LIMIT ?
        """,
        (user_id, limit),
    )
    return [summary_row(row) for row in rows]


def get(db: Database, user_id: int, attempt_id: int) -> dict[str, Any] | None:
    row = db.fetch_one(
        "SELECT * FROM attempts WHERE id = ? AND user_id = ?", (attempt_id, user_id)
    )
    return _row_to_dict(row) if row else None


def _aggregate(row: Mapping[str, Any]) -> dict[str, Any]:
    # PostgreSQL returns AVG as Decimal, SQLite as float.
    average = row["average"]
    return {
        "taken": int(row["taken"] or 0),
        "best": int(row["best"]) if row["best"] is not None else None,
        "average": round(float(average)) if average is not None else None,
    }


def summary(db: Database, user_id: int) -> dict[str, Any]:
    """Counts the lobby dashboard shows: over every attempt, and per section.

    A math score and a Reading and Writing score are different scales of the
    same 200-800 range, so the per-section figures are the ones worth
    comparing; the overall ones are kept for what the dashboard showed before.
    """
    overall = db.fetch_one(
        """
        SELECT COUNT(*) AS taken, MAX(score) AS best, AVG(score) AS average
        FROM attempts WHERE user_id = ?
        """,
        (user_id,),
    )
    rows = db.fetch_all(
        """
        SELECT section, COUNT(*) AS taken, MAX(score) AS best, AVG(score) AS average
        FROM attempts WHERE user_id = ? GROUP BY section
        """,
        (user_id,),
    )
    by_section = {section: {"taken": 0, "best": None, "average": None} for section in SECTION_KEYS}
    for row in rows:
        by_section[str(row["section"] or DEFAULT_SECTION)] = _aggregate(row)
    return {**_aggregate(overall), "by_section": by_section}
