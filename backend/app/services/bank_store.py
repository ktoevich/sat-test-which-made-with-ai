"""The question bank held in the database rather than in a file.

A serverless host builds its filesystem from the repository, so a bank that is
not committed never reaches the deployment. Putting the bundles in the database
the app already needs for accounts keeps them out of the repository without
giving up push-to-deploy.

Each bundle is one row, so serving a module reads a single test rather than the
whole bank — which matters when the bank is megabytes and every request is a
cold function.
"""

from __future__ import annotations

import json
import random
from datetime import datetime, timezone
from typing import Any, Sequence

from ..db import Database

Bundle = dict[str, Any]

TABLE = "question_bundles"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def count(database: Database) -> int:
    row = database.fetch_one(f"SELECT COUNT(*) AS total FROM {TABLE}")
    return int(row["total"]) if row else 0


def test_ids(database: Database) -> list[str]:
    rows = database.fetch_all(f"SELECT test_id FROM {TABLE} ORDER BY position, test_id")
    return [str(row["test_id"]) for row in rows]


def fetch(database: Database, test_id: str) -> Bundle | None:
    row = database.fetch_one(f"SELECT payload FROM {TABLE} WHERE test_id = ?", (test_id,))
    return json.loads(row["payload"]) if row else None


def fetch_random(database: Database, rng: random.Random | None = None) -> Bundle | None:
    """One bundle, chosen without reading the payload of any of the others."""
    ids = test_ids(database)
    if not ids:
        return None
    return fetch(database, (rng or random).choice(ids))


def fetch_all(database: Database) -> list[Bundle]:
    """Every bundle. Only for the CLI and the export — a request never needs it."""
    rows = database.fetch_all(f"SELECT payload FROM {TABLE} ORDER BY position, test_id")
    return [json.loads(row["payload"]) for row in rows]


def replace_all(database: Database, bank: Sequence[Bundle]) -> int:
    """Swap the stored bank for ``bank``, in one transaction.

    The old rows go before the new ones land, so a bundle dropped from the bank
    does not linger and get served.
    """
    stamp = _now()
    try:
        database.execute(f"DELETE FROM {TABLE}")
        for position, bundle in enumerate(bank):
            database.execute(
                f"INSERT INTO {TABLE} (test_id, position, payload, updated_at) VALUES (?, ?, ?, ?)",
                (
                    str(bundle["test_id"]),
                    position,
                    json.dumps(bundle, ensure_ascii=False),
                    stamp,
                ),
            )
        database.commit()
    except Exception:
        database.rollback()
        raise
    return len(bank)


def clear(database: Database) -> int:
    """Empty the stored bank, so the app falls back to the file again."""
    removed = count(database)
    database.execute(f"DELETE FROM {TABLE}")
    database.commit()
    return removed


def updated_at(database: Database) -> str | None:
    row = database.fetch_one(f"SELECT MAX(updated_at) AS stamp FROM {TABLE}")
    return str(row["stamp"]) if row and row["stamp"] else None
