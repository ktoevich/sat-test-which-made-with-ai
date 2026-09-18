"""Friends and messages between students.

A friendship starts as a request from one student to another and becomes
mutual when the other accepts; sending a request to someone who has already
sent you one accepts theirs. Messages are plain text between any two
students, read when the recipient opens the thread.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from ..db import Database
from . import accounts

PENDING = "pending"
ACCEPTED = "accepted"

MAX_MESSAGE_LENGTH = 2000
THREAD_LIMIT = 200


class SocialError(accounts.AccountError):
    code = "social_error"


class NotAllowed(SocialError):
    code = "not_allowed"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _user(db: Database, user_id: int) -> accounts.User:
    row = db.fetch_one("SELECT * FROM users WHERE id = ? AND is_disabled = 0", (user_id,))
    if row is None:
        raise accounts.UserNotFound("That student does not exist.")
    return accounts.User.from_row(row)


# -- friendships -------------------------------------------------------------


def _pair(db: Database, a: int, b: int) -> dict[str, Any] | None:
    return db.fetch_one(
        """
        SELECT * FROM friendships
        WHERE (requester_id = ? AND addressee_id = ?) OR (requester_id = ? AND addressee_id = ?)
        """,
        (a, b, b, a),
    )


def relationship(db: Database, viewer_id: int, other_id: int) -> str:
    """``self``, ``friends``, ``incoming`` (they asked), ``outgoing`` (you asked) or ``none``."""
    if viewer_id == other_id:
        return "self"
    row = _pair(db, viewer_id, other_id)
    if row is None:
        return "none"
    if row["status"] == ACCEPTED:
        return "friends"
    return "outgoing" if int(row["requester_id"]) == int(viewer_id) else "incoming"


def friends_count(db: Database, user_id: int) -> int:
    row = db.fetch_one(
        "SELECT COUNT(*) AS n FROM friendships WHERE status = ? AND (requester_id = ? OR addressee_id = ?)",
        (ACCEPTED, user_id, user_id),
    )
    return int(row["n"] or 0)


def overview(db: Database, user_id: int) -> dict[str, Any]:
    """Friends, requests waiting for this student, and requests they sent."""
    # Column names are spelled out: ``u.*`` also has a ``created_at`` and an
    # ``id``, and the two engines resolve a duplicated name differently.
    rows = db.fetch_all(
        """
        SELECT f.id AS request_id, f.status, f.created_at AS since, f.requester_id AS asked_by,
               u.id, u.email, u.username, u.created_at, u.last_login_at, u.is_disabled,
               u.avatar, u.full_name, u.location, u.rating, u.max_rating, u.top_score
        FROM friendships f
        JOIN users u ON u.id = CASE WHEN f.requester_id = ? THEN f.addressee_id ELSE f.requester_id END
        WHERE (f.requester_id = ? OR f.addressee_id = ?) AND u.is_disabled = 0
        ORDER BY f.created_at DESC
        """,
        (user_id, user_id, user_id),
    )
    friends, incoming, outgoing = [], [], []
    for row in rows:
        entry = {
            "request_id": int(row["request_id"]),
            "since": row["since"],
            "user": accounts.User.from_row(row).public_dict(),
        }
        if row["status"] == ACCEPTED:
            friends.append(entry)
        elif int(row["asked_by"]) == int(user_id):
            outgoing.append(entry)
        else:
            incoming.append(entry)
    return {"friends": friends, "incoming": incoming, "outgoing": outgoing}


def send_request(db: Database, user_id: int, other_id: int) -> dict[str, Any]:
    """Ask to be friends. Answering a request the other way round accepts it."""
    if int(user_id) == int(other_id):
        raise NotAllowed("You cannot add yourself.")
    _user(db, other_id)
    existing = _pair(db, user_id, other_id)
    if existing is not None:
        if existing["status"] == ACCEPTED:
            raise NotAllowed("You are already friends.")
        if int(existing["requester_id"]) == int(user_id):
            raise NotAllowed("You have already sent a request.")
        return accept_request(db, user_id, int(existing["id"]))
    db.insert(
        "INSERT INTO friendships (requester_id, addressee_id, status, created_at) VALUES (?, ?, ?, ?)",
        (user_id, other_id, PENDING, _now()),
    )
    db.commit()
    return {"relationship": "outgoing"}


def accept_request(db: Database, user_id: int, request_id: int) -> dict[str, Any]:
    row = db.fetch_one("SELECT * FROM friendships WHERE id = ?", (request_id,))
    if row is None or int(row["addressee_id"]) != int(user_id) or row["status"] != PENDING:
        raise NotAllowed("There is no such request waiting for you.")
    db.execute(
        "UPDATE friendships SET status = ?, created_at = ? WHERE id = ?", (ACCEPTED, _now(), request_id)
    )
    db.commit()
    return {"relationship": "friends"}


def remove_request(db: Database, user_id: int, request_id: int) -> None:
    """Decline a request sent to you, or take back one you sent."""
    row = db.fetch_one("SELECT * FROM friendships WHERE id = ? AND status = ?", (request_id, PENDING))
    if row is None or int(user_id) not in (int(row["requester_id"]), int(row["addressee_id"])):
        raise NotAllowed("There is no such request.")
    db.execute("DELETE FROM friendships WHERE id = ?", (request_id,))
    db.commit()


def unfriend(db: Database, user_id: int, other_id: int) -> None:
    row = _pair(db, user_id, other_id)
    if row is None or row["status"] != ACCEPTED:
        raise NotAllowed("You are not friends.")
    db.execute("DELETE FROM friendships WHERE id = ?", (row["id"],))
    db.commit()


# -- messages ----------------------------------------------------------------


def _message(row: Any) -> dict[str, Any]:
    return {
        "id": int(row["id"]),
        "sender_id": int(row["sender_id"]),
        "recipient_id": int(row["recipient_id"]),
        "body": row["body"],
        "sent_at": row["sent_at"],
        "read_at": row["read_at"],
    }


def conversations(db: Database, user_id: int) -> list[dict[str, Any]]:
    """Everyone this student has exchanged messages with, latest first, with unread counts."""
    rows = db.fetch_all(
        """
        SELECT m.sender_id, m.recipient_id, m.body, m.sent_at, m.read_at,
               u.id, u.email, u.username, u.created_at, u.last_login_at, u.is_disabled,
               u.avatar, u.full_name, u.location, u.rating, u.max_rating, u.top_score
        FROM messages m
        JOIN users u ON u.id = CASE WHEN m.sender_id = ? THEN m.recipient_id ELSE m.sender_id END
        WHERE (m.sender_id = ? OR m.recipient_id = ?) AND u.is_disabled = 0
        ORDER BY m.id DESC
        """,
        (user_id, user_id, user_id),
    )
    seen: dict[int, dict[str, Any]] = {}
    for row in rows:
        other = accounts.User.from_row(row)
        entry = seen.get(other.id)
        if entry is None:
            entry = seen[other.id] = {
                "user": other.public_dict(),
                "last_message": {
                    "body": row["body"],
                    "sent_at": row["sent_at"],
                    "mine": int(row["sender_id"]) == int(user_id),
                },
                "unread": 0,
            }
        if int(row["recipient_id"]) == int(user_id) and row["read_at"] is None:
            entry["unread"] += 1
    return list(seen.values())


def unread_count(db: Database, user_id: int) -> int:
    row = db.fetch_one(
        "SELECT COUNT(*) AS n FROM messages WHERE recipient_id = ? AND read_at IS NULL", (user_id,)
    )
    return int(row["n"] or 0)


def thread(db: Database, user_id: int, other_id: int) -> dict[str, Any]:
    """The messages between two students, oldest first; reading marks theirs as read."""
    other = _user(db, other_id)
    db.execute(
        "UPDATE messages SET read_at = ? WHERE recipient_id = ? AND sender_id = ? AND read_at IS NULL",
        (_now(), user_id, other_id),
    )
    db.commit()
    rows = db.fetch_all(
        """
        SELECT * FROM (
            SELECT * FROM messages
            WHERE (sender_id = ? AND recipient_id = ?) OR (sender_id = ? AND recipient_id = ?)
            ORDER BY id DESC LIMIT ?
        ) latest ORDER BY id ASC
        """,
        (user_id, other_id, other_id, user_id, THREAD_LIMIT),
    )
    return {"user": other.public_dict(), "messages": [_message(row) for row in rows]}


def send_message(db: Database, user_id: int, other_id: int, body: str) -> dict[str, Any]:
    if int(user_id) == int(other_id):
        raise NotAllowed("You cannot message yourself.")
    _user(db, other_id)
    text = str(body or "").strip()
    if not text:
        raise accounts.ValidationFailed("Write something first.")
    if len(text) > MAX_MESSAGE_LENGTH:
        raise accounts.ValidationFailed(f"A message can be at most {MAX_MESSAGE_LENGTH} characters.")
    message_id = db.insert(
        "INSERT INTO messages (sender_id, recipient_id, body, sent_at) VALUES (?, ?, ?, ?)",
        (user_id, other_id, text, _now()),
    )
    db.commit()
    return _message(db.fetch_one("SELECT * FROM messages WHERE id = ?", (message_id,)))
