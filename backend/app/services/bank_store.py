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

from ..bank.ordering import bundle_section
from ..db import Database

Bundle = dict[str, Any]

TABLE = "question_bundles"


def _where(section: str | None) -> tuple[str, tuple]:
    """A filter on the section, or none at all."""
    return (" WHERE section = ?", (section,)) if section else ("", ())


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def count(database: Database, section: str | None = None) -> int:
    """How many tests are stored, in one section or in all of them."""
    where, params = _where(section)
    row = database.fetch_one(f"SELECT COUNT(*) AS total FROM {TABLE}{where}", params)
    return int(row["total"]) if row else 0


def counts_by_section(database: Database) -> dict[str, int]:
    rows = database.fetch_all(f"SELECT section, COUNT(*) AS total FROM {TABLE} GROUP BY section")
    return {str(row["section"]): int(row["total"]) for row in rows}


def test_ids(database: Database, section: str | None = None) -> list[str]:
    where, params = _where(section)
    rows = database.fetch_all(f"SELECT test_id FROM {TABLE}{where} ORDER BY position, test_id", params)
    return [str(row["test_id"]) for row in rows]


def fetch(database: Database, test_id: str) -> Bundle | None:
    row = database.fetch_one(f"SELECT payload FROM {TABLE} WHERE test_id = ?", (test_id,))
    return json.loads(row["payload"]) if row else None


def fetch_random(
    database: Database, rng: random.Random | None = None, section: str | None = None
) -> Bundle | None:
    """One bundle of ``section``, chosen without reading the payload of any of the others."""
    ids = test_ids(database, section)
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
                f"INSERT INTO {TABLE} (test_id, section, position, payload, updated_at) "
                "VALUES (?, ?, ?, ?, ?)",
                (
                    str(bundle["test_id"]),
                    bundle_section(bundle),
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
