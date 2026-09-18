"""What happened to a student while they were away: friend requests and answers.

A notification names who did it (``actor``), what (``kind``) and the row it
is about (``ref_id``: the friendship for both kinds). The wording is left to
the page, so it follows the student's language. A request that is declined or
taken back takes its notification with it; one that is accepted stays, read,
without the buttons.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from ..db import Database
from . import accounts

FRIEND_REQUEST = "friend_request"
FRIEND_ACCEPTED = "friend_accepted"

LIMIT = 30


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def notify(db: Database, user_id: int, kind: str, *, actor_id: int, ref_id: int | None = None) -> None:
    """Record a notification. The caller commits it with whatever caused it."""
    db.insert(
        "INSERT INTO notifications (user_id, actor_id, kind, ref_id, created_at) VALUES (?, ?, ?, ?, ?)",
        (user_id, actor_id, kind, ref_id, _now()),
    )


def settle_request(db: Database, request_id: int, *, remove: bool) -> None:
    """A friend request was answered: its notification is read, or gone with it."""
    if remove:
        db.execute("DELETE FROM notifications WHERE kind = ? AND ref_id = ?", (FRIEND_REQUEST, request_id))
    else:
        db.execute(
            "UPDATE notifications SET read_at = ? WHERE kind = ? AND ref_id = ? AND read_at IS NULL",
            (_now(), FRIEND_REQUEST, request_id),
        )


def unread_count(db: Database, user_id: int) -> int:
    row = db.fetch_one(
        "SELECT COUNT(*) AS n FROM notifications WHERE user_id = ? AND read_at IS NULL", (user_id,)
    )
    return int(row["n"] or 0)


def listing(db: Database, user_id: int, *, limit: int = LIMIT) -> dict[str, Any]:
    """The latest notifications, newest first, and how many are unread."""
    # Column names are spelled out for the same reason as in social.overview.
    rows = db.fetch_all(
        """
        SELECT n.id AS notification_id, n.kind, n.ref_id, n.created_at AS notified_at, n.read_at,
               f.status AS request_status,
               u.id, u.email, u.username, u.created_at, u.last_login_at, u.is_disabled,
               u.avatar, u.full_name, u.location, u.rating, u.max_rating, u.top_score
        FROM notifications n
        JOIN users u ON u.id = n.actor_id
        LEFT JOIN friendships f ON f.id = n.ref_id
        WHERE n.user_id = ? AND u.is_disabled = 0
        ORDER BY n.id DESC
        LIMIT ?
        """,
        (user_id, max(1, min(int(limit), 100))),
    )
    items = [
        {
            "id": int(row["notification_id"]),
            "kind": row["kind"],
            "ref_id": int(row["ref_id"]) if row["ref_id"] is not None else None,
            "created_at": row["notified_at"],
            "read": row["read_at"] is not None,
            # A request can still be answered from the notification only while it waits.
            "pending": row["kind"] == FRIEND_REQUEST and row["request_status"] == "pending",
            "user": accounts.User.from_row(row).public_dict(),
        }
        for row in rows
    ]
    return {"notifications": items, "unread": unread_count(db, user_id)}


def mark_read(db: Database, user_id: int, notification_id: int | None = None) -> int:
    """Mark one notification, or all of them, as read. Returns what is still unread."""
    if notification_id is None:
        db.execute(
            "UPDATE notifications SET read_at = ? WHERE user_id = ? AND read_at IS NULL", (_now(), user_id)
        )
    else:
        db.execute(
            "UPDATE notifications SET read_at = ? WHERE user_id = ? AND id = ? AND read_at IS NULL",
            (_now(), user_id, notification_id),
        )
    db.commit()
    return unread_count(db, user_id)
