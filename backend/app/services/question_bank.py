"""Access layer for the pre-generated test bundles.

Bundles come from the database when it holds any, and from the bank file
otherwise. A deployment that cannot commit its bank pushes it into the database
instead (``app.cli bank push``); everything else keeps working off the file with
no database at all, which is what makes the app usable before one is attached.
"""

from __future__ import annotations

import json
import logging
import random
from pathlib import Path
from typing import Any

from . import bank_store

logger = logging.getLogger(__name__)

Bundle = dict[str, Any]

MODULE_1_KEY = "module_1"
MODULE_2_KEY_TEMPLATE = "module_2_{target}"
VALID_TARGETS = ("HIGHER", "LOWER")


class QuestionBankError(RuntimeError):
    """Raised when the requested slice of the bank does not exist."""


class QuestionBank:
    """Serves bundles from the database if it has them, else from the file.

    The file is read lazily and re-read when its modification time changes. The
    database is consulted first but never allowed to break the bank: if it is
    unreachable — no ``DATABASE_URL`` yet, a cold serverless start, the CLI
    running outside an app context — the file answers instead.
    """

    def __init__(self, path: str | Path, *, use_database: bool = True) -> None:
        self.path = Path(path)
        self.use_database = use_database
        self._bundles: list[Bundle] = []
        self._mtime: float | None = None

    # -- the database ----------------------------------------------------

    def _database(self):
        """The request's connection, or None when there is not one to use."""
        if not self.use_database:
            return None
        try:
            from ..db import get_db

            return get_db()
        except Exception:
            # DatabaseUnavailable, or no application context at all. Either way
            # the file is the answer, and a missing database is not an error
            # the student should ever see.
            return None

    def _stored_count(self) -> int | None:
        """How many tests the database holds, or None when it cannot say."""
        database = self._database()
        if database is None:
            return None
        try:
            return bank_store.count(database)
        except Exception:
            logger.warning("Could not read the stored question bank", exc_info=True)
            return None

    def _stored(self, read):
        """Run ``read`` against the stored bank, or None if there is nothing to read.

        A miss falls through to the file, so no separate count is needed first —
        which keeps a served module down to one round trip more than it has to
        make anyway.
        """
        database = self._database()
        if database is None:
            return None
        try:
            return read(database)
        except Exception:
            logger.warning("Could not read the stored question bank", exc_info=True)
            return None

    # -- loading ---------------------------------------------------------

    def _read_file(self) -> list[Bundle]:
        try:
            with self.path.open(encoding="utf-8") as handle:
                data = json.load(handle)
        except FileNotFoundError:
            logger.warning("Question bank not found at %s", self.path)
            return []
        except json.JSONDecodeError:
            logger.exception("Question bank at %s is not valid JSON", self.path)
            return []

        if not isinstance(data, list):
            logger.error("Question bank at %s must contain a list of bundles", self.path)
            return []
        return data

    def load(self) -> list[Bundle]:
        """Return all bundles, re-reading the file only when it was modified."""
        try:
            mtime = self.path.stat().st_mtime
        except OSError:
            self._bundles, self._mtime = [], None
            return []

        if mtime != self._mtime:
            self._bundles = self._read_file()
            self._mtime = mtime
        return self._bundles

    def count(self) -> int:
        """How many tests can be served, without reading any of them."""
        stored = self._stored_count()
        return stored if stored else len(self.load())

    @property
    def is_empty(self) -> bool:
        return self.count() == 0

    # -- queries ---------------------------------------------------------

    def random_bundle(self, *, rng: random.Random | None = None) -> Bundle:
        bundle = self._stored(lambda database: bank_store.fetch_random(database, rng))
        if bundle is not None:
            return bundle

        bundles = self.load()
        if not bundles:
            raise QuestionBankError("The question bank is empty")
        return (rng or random).choice(bundles)

    def get_bundle(self, test_id: str | None) -> Bundle | None:
        if not test_id:
            return None

        bundle = self._stored(lambda database: bank_store.fetch(database, test_id))
        if bundle is not None:
            return bundle

        return next((b for b in self.load() if b.get("test_id") == test_id), None)

    def module_1(self, bundle: Bundle) -> list[dict[str, Any]]:
        return self._section(bundle, MODULE_1_KEY)

    def module_2(self, bundle: Bundle, target: str) -> list[dict[str, Any]]:
        normalised = (target or "").upper()
        if normalised not in VALID_TARGETS:
            raise QuestionBankError(
                f"Unknown module 2 target {target!r}; expected one of {VALID_TARGETS}"
            )
        return self._section(bundle, MODULE_2_KEY_TEMPLATE.format(target=normalised))

    @staticmethod
    def _section(bundle: Bundle, key: str) -> list[dict[str, Any]]:
        section = bundle.get(key)
        if not isinstance(section, list) or not section:
            raise QuestionBankError(
                f"Bundle {bundle.get('test_id', '<unknown>')!r} has no questions under {key!r}"
            )
        return section
