"""User accounts and login sessions."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Mapping

from ..db import Database
from ..security import (
    hash_password,
    needs_rehash,
    new_token,
    token_fingerprint,
    verify_password,
)

#: How long a login stays valid.
SESSION_LIFETIME = timedelta(days=30)

MIN_PASSWORD_LENGTH = 8
MAX_EMAIL_LENGTH = 254
MAX_USERNAME_LENGTH = 40


class AccountError(Exception):
    """Base class for problems the caller should show to the user."""

    code = "account_error"


class EmailTaken(AccountError):
    code = "email_taken"


class InvalidCredentials(AccountError):
    code = "invalid_credentials"


class AccountDisabled(AccountError):
    code = "account_disabled"


class ValidationFailed(AccountError):
    code = "validation_failed"


class UserNotFound(AccountError):
    code = "user_not_found"


@dataclass(frozen=True)
class User:
    id: int
    email: str
    username: str
    created_at: str
    last_login_at: str | None
    is_disabled: bool

    @classmethod
    def from_row(cls, row: Mapping[str, Any]) -> "User":
        return cls(
            id=row["id"],
            email=row["email"],
            username=row["username"],
            created_at=row["created_at"],
            last_login_at=row["last_login_at"],
            is_disabled=bool(row["is_disabled"]),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "email": self.email,
            "username": self.username,
            "created_at": self.created_at,
            "last_login_at": self.last_login_at,
            "is_disabled": self.is_disabled,
        }


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def normalise_email(email: str) -> str:
    return str(email or "").strip().lower()


def _validate(email: str, username: str, password: str) -> None:
    if not email or "@" not in email or len(email) > MAX_EMAIL_LENGTH:
        raise ValidationFailed("Enter a valid email address.")
    if not username or len(username) > MAX_USERNAME_LENGTH:
        raise ValidationFailed(f"Username must be 1-{MAX_USERNAME_LENGTH} characters.")
    if len(password) < MIN_PASSWORD_LENGTH:
        raise ValidationFailed(f"Password must be at least {MIN_PASSWORD_LENGTH} characters.")


# -- accounts ----------------------------------------------------------


def register(
    db: Database, *, email: str, username: str, password: str, iterations: int
) -> User:
    """Create an account. Raises :class:`EmailTaken` if the email is in use."""
    email = normalise_email(email)
    username = str(username or "").strip()
    _validate(email, username, password)

    if find_by_email(db, email) is not None:
        raise EmailTaken("An account with this email already exists.")

    user_id = db.insert(
        "INSERT INTO users (email, username, password_hash, created_at) VALUES (?, ?, ?, ?)",
        (email, username, hash_password(password, iterations=iterations), _now()),
    )
    db.commit()
    return get_user(db, user_id)


def authenticate(
    db: Database, *, email: str, password: str, iterations: int
) -> User:
    """Check credentials and record the login."""
    row = db.fetch_one("SELECT * FROM users WHERE email = ?", (normalise_email(email),))

    if row is None:
        # Spend the same work as a real check so timing does not reveal whether
        # the address exists.
        verify_password(password, hash_password("placeholder", iterations=iterations))
        raise InvalidCredentials("Email or password is incorrect.")

    if not verify_password(password, row["password_hash"]):
        raise InvalidCredentials("Email or password is incorrect.")

    if row["is_disabled"]:
        raise AccountDisabled("This account has been disabled.")

    updates: list[str] = ["last_login_at = ?"]
    params: list[Any] = [_now()]
    if needs_rehash(row["password_hash"], iterations=iterations):
        updates.append("password_hash = ?")
        params.append(hash_password(password, iterations=iterations))

    params.append(row["id"])
    db.execute(f"UPDATE users SET {', '.join(updates)} WHERE id = ?", params)
    db.commit()

    return get_user(db, row["id"])


def get_user(db: Database, user_id: int) -> User:
    row = db.fetch_one("SELECT * FROM users WHERE id = ?", (user_id,))
    if row is None:
        raise UserNotFound(f"No user with id {user_id}")
    return User.from_row(row)


def find_by_email(db: Database, email: str) -> User | None:
    row = db.fetch_one("SELECT * FROM users WHERE email = ?", (normalise_email(email),))
    return User.from_row(row) if row else None


def list_users(db: Database, *, search: str | None = None, limit: int = 100) -> list[dict]:
    """Accounts with their attempt counts, newest first — the admin view."""
    sql = """
        SELECT u.*,
               COUNT(a.id) AS attempts,
               MAX(a.score) AS best_score
        FROM users u
        LEFT JOIN attempts a ON a.user_id = u.id
    """
    params: list[Any] = []
    if search:
        sql += " WHERE u.email LIKE ? OR u.username LIKE ?"
        params += [f"%{search}%", f"%{search}%"]
    sql += " GROUP BY u.id ORDER BY u.created_at DESC LIMIT ?"
    params.append(limit)

    return [
        User.from_row(row).to_dict()
        | {"attempts": int(row["attempts"]), "best_score": row["best_score"]}
        for row in db.fetch_all(sql, params)
    ]


def set_password(db: Database, user_id: int, password: str, *, iterations: int) -> None:
    """Replace a password and end every existing session for that user."""
    if len(password) < MIN_PASSWORD_LENGTH:
        raise ValidationFailed(f"Password must be at least {MIN_PASSWORD_LENGTH} characters.")

    db.execute(
        "UPDATE users SET password_hash = ? WHERE id = ?",
        (hash_password(password, iterations=iterations), user_id),
    )
    db.execute("DELETE FROM sessions WHERE user_id = ?", (user_id,))
    db.commit()


def set_disabled(db: Database, user_id: int, disabled: bool) -> None:
    db.execute("UPDATE users SET is_disabled = ? WHERE id = ?", (int(disabled), user_id))
    if disabled:
        db.execute("DELETE FROM sessions WHERE user_id = ?", (user_id,))
    db.commit()


def delete_user(db: Database, user_id: int) -> None:
    """Remove an account together with its sessions and attempts."""
    db.execute("DELETE FROM users WHERE id = ?", (user_id,))
    db.commit()


# -- sessions ----------------------------------------------------------


def start_session(db: Database, user_id: int) -> str:
    """Issue a token. Only its fingerprint is stored."""
    token = new_token()
    expires = datetime.now(timezone.utc) + SESSION_LIFETIME
    db.execute(
        "INSERT INTO sessions (token_hash, user_id, created_at, expires_at) VALUES (?, ?, ?, ?)",
        (token_fingerprint(token), user_id, _now(), expires.isoformat(timespec="seconds")),
    )
    db.commit()
    return token


def user_for_token(db: Database, token: str) -> User | None:
    """Resolve a token, dropping it if it has expired."""
    if not token:
        return None

    row = db.fetch_one(
        """
        SELECT u.*, s.expires_at
        FROM sessions s JOIN users u ON u.id = s.user_id
        WHERE s.token_hash = ?
        """,
        (token_fingerprint(token),),
    )

    if row is None:
        return None

    if datetime.fromisoformat(row["expires_at"]) <= datetime.now(timezone.utc):
        end_session(db, token)
        return None

    return None if row["is_disabled"] else User.from_row(row)


def end_session(db: Database, token: str) -> None:
    db.execute("DELETE FROM sessions WHERE token_hash = ?", (token_fingerprint(token),))
    db.commit()
