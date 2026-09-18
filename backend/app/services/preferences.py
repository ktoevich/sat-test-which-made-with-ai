"""Interface settings kept with the account, so they follow a student between devices.

Only known keys with known values are stored: the page reads them back and
applies them, so anything else would be noise at best.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Mapping

from ..db import Database
from . import accounts

#: Each setting and the values it may take.
ALLOWED: dict[str, tuple[str, ...]] = {
    "theme": ("light", "dark"),
    "language": ("en", "ru"),
}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def get(db: Database, user_id: int) -> dict[str, str]:
    row = db.fetch_one("SELECT settings FROM user_settings WHERE user_id = ?", (user_id,))
    if row is None:
        return {}
    try:
        stored = json.loads(row["settings"] or "{}")
    except ValueError:
        return {}
    # A value that is no longer allowed is dropped rather than handed back.
    return {key: value for key, value in stored.items() if value in ALLOWED.get(key, ())}


def update(db: Database, user_id: int, changes: Mapping[str, Any]) -> dict[str, str]:
    """Merge ``changes`` into what is stored. Keys left out are kept."""
    if not isinstance(changes, Mapping) or not changes:
        raise accounts.ValidationFailed("Nothing to change.")
    for key, value in changes.items():
        if key not in ALLOWED:
            raise accounts.ValidationFailed(f"Unknown setting {key!r}.")
        if value not in ALLOWED[key]:
            raise accounts.ValidationFailed(f"{key} must be one of {', '.join(ALLOWED[key])}.")
    settings = {**get(db, user_id), **changes}
    db.execute(
        """
        INSERT INTO user_settings (user_id, settings, updated_at) VALUES (?, ?, ?)
        ON CONFLICT (user_id) DO UPDATE SET settings = excluded.settings, updated_at = excluded.updated_at
        """,
        (user_id, json.dumps(settings, sort_keys=True), _now()),
    )
    db.commit()
    return settings
