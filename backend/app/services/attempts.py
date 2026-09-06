"""Finished test attempts, stored per user."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Mapping

from ..db import Database

#: Cap on the stored per-question breakdown, so one attempt cannot bloat the DB.
MAX_DETAIL_QUESTIONS = 200


def _row_to_dict(row: Mapping[str, Any]) -> dict[str, Any]:
    try:
        details = json.loads(row["details"])
    except (json.JSONDecodeError, TypeError):
        details = []
    return {
        "id": int(row["id"]),
        "taken_at": row["taken_at"],
        "score": row["score"],
        "correct": row["correct"],
        "total": row["total"],
        "details": details,
    }


def record(
    db: Database,
    *,
    user_id: int,
    score: int,
    correct: int,
    total: int,
    details: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Save one finished attempt and return it."""
    trimmed = (details or [])[:MAX_DETAIL_QUESTIONS]
    attempt_id = db.insert(
        """
        INSERT INTO attempts (user_id, taken_at, score, correct, total, details)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            user_id,
            datetime.now(timezone.utc).isoformat(timespec="seconds"),
            int(score),
            int(correct),
            int(total),
            json.dumps(trimmed, ensure_ascii=False),
        ),
    )
    db.commit()
    return get(db, user_id, attempt_id)


def list_for_user(db: Database, user_id: int, *, limit: int = 50) -> list[dict[str, Any]]:
    """A user's attempts, newest first."""
    rows = db.fetch_all(
        "SELECT * FROM attempts WHERE user_id = ? ORDER BY taken_at DESC, id DESC LIMIT ?",
        (user_id, limit),
    )
    return [_row_to_dict(row) for row in rows]


def get(db: Database, user_id: int, attempt_id: int) -> dict[str, Any] | None:
    row = db.fetch_one(
        "SELECT * FROM attempts WHERE id = ? AND user_id = ?", (attempt_id, user_id)
    )
    return _row_to_dict(row) if row else None


def summary(db: Database, user_id: int) -> dict[str, Any]:
    """Counts the lobby dashboard shows."""
    row = db.fetch_one(
        """
        SELECT COUNT(*) AS taken, MAX(score) AS best, AVG(score) AS average
        FROM attempts WHERE user_id = ?
        """,
        (user_id,),
    )

    # PostgreSQL returns AVG as Decimal, SQLite as float.
    average = row["average"]
    return {
        "taken": int(row["taken"] or 0),
        "best": int(row["best"]) if row["best"] is not None else None,
        "average": round(float(average)) if average is not None else None,
    }
