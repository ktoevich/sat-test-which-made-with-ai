"""Access layer for the pre-generated test bundles stored on disk."""

from __future__ import annotations

import json
import logging
import random
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

Bundle = dict[str, Any]

MODULE_1_KEY = "module_1"
MODULE_2_KEY_TEMPLATE = "module_2_{target}"
VALID_TARGETS = ("HIGHER", "LOWER")


class QuestionBankError(RuntimeError):
    """Raised when the requested slice of the bank does not exist."""


class QuestionBank:
    """Reads the bundle file lazily and reloads it when the file changes."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self._bundles: list[Bundle] = []
        self._mtime: float | None = None

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

    @property
    def is_empty(self) -> bool:
        return not self.load()

    # -- queries ---------------------------------------------------------

    def random_bundle(self, *, rng: random.Random | None = None) -> Bundle:
        bundles = self.load()
        if not bundles:
            raise QuestionBankError("The question bank is empty")
        return (rng or random).choice(bundles)

    def get_bundle(self, test_id: str | None) -> Bundle | None:
        if not test_id:
            return None
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
