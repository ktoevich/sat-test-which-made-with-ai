"""Password hashing and session tokens.

Uses only the standard library: PBKDF2-HMAC-SHA256 for passwords and
``secrets`` for tokens. Passwords are stored as a one-way hash and cannot be
read back — recovery means resetting to a new password, never revealing the old.
"""

from __future__ import annotations

import hashlib
import hmac
import secrets

ALGORITHM = "pbkdf2_sha256"
#: OWASP's current floor for PBKDF2-HMAC-SHA256.
DEFAULT_ITERATIONS = 600_000
SALT_BYTES = 16
TOKEN_BYTES = 32


def hash_password(password: str, *, iterations: int = DEFAULT_ITERATIONS) -> str:
    """Return ``algorithm$iterations$salt$hash``, safe to store."""
    salt = secrets.token_bytes(SALT_BYTES)
    digest = _derive(password, salt, iterations)
    return f"{ALGORITHM}${iterations}${salt.hex()}${digest.hex()}"


def verify_password(password: str, stored: str) -> bool:
    """Check a password against a stored hash, in constant time."""
    try:
        algorithm, iterations, salt_hex, digest_hex = stored.split("$")
        if algorithm != ALGORITHM:
            return False
        expected = bytes.fromhex(digest_hex)
        actual = _derive(password, bytes.fromhex(salt_hex), int(iterations))
    except (ValueError, AttributeError):
        return False
    return hmac.compare_digest(expected, actual)


def needs_rehash(stored: str, *, iterations: int = DEFAULT_ITERATIONS) -> bool:
    """True when a stored hash uses weaker settings than the current policy."""
    try:
        algorithm, stored_iterations, _, _ = stored.split("$")
    except ValueError:
        return True
    return algorithm != ALGORITHM or int(stored_iterations) < iterations


def _derive(password: str, salt: bytes, iterations: int) -> bytes:
    return hashlib.pbkdf2_hmac("sha256", password.encode(), salt, iterations)


def new_token() -> str:
    """A fresh, unguessable session token."""
    return secrets.token_urlsafe(TOKEN_BYTES)


def token_fingerprint(token: str) -> str:
    """What actually goes in the database, so a dump cannot be replayed."""
    return hashlib.sha256(token.encode()).hexdigest()


def temporary_password(length: int = 12) -> str:
    """A readable one-time password for an admin-driven reset."""
    alphabet = "abcdefghijkmnpqrstuvwxyzABCDEFGHJKLMNPQRSTUVWXYZ23456789"
    return "".join(secrets.choice(alphabet) for _ in range(length))
