"""Practice one content domain at a time: a handful of questions, checked as you go.

The questions come from the same bank the tests do. Reading whole bundles is
how the bank is stored, so a practice set is drawn from a few random tests of
the section and filtered to the domain — enough variety for a short session
without loading the entire bank on every request.
"""

from __future__ import annotations

import random
from typing import Any

from ..bank.schema import MODULE_KEYS
from ..bank.taxonomy import section_of

DEFAULT_COUNT = 5
MAX_COUNT = 20
#: How many random tests to look through for a domain's questions.
BUNDLES_TO_SAMPLE = 3


def practice_questions(
    bank,
    *,
    section: str | None,
    domain: str | None = None,
    skill: str | None = None,
    count: int = DEFAULT_COUNT,
    rng: random.Random | None = None,
) -> list[dict[str, Any]]:
    """``count`` questions of ``section`` about ``domain`` (or ``skill``), numbered from 1."""
    rng = rng or random.Random()
    section_key = section_of(section).key
    count = max(1, min(MAX_COUNT, int(count or DEFAULT_COUNT)))

    seen: set[str] = set()
    pool: list[dict[str, Any]] = []
    for _ in range(BUNDLES_TO_SAMPLE):
        try:
            bundle = bank.random_bundle(rng=rng, section=section_key)
        except Exception:
            break
        for key in MODULE_KEYS:
            for question in bundle.get(key, []) or []:
                if domain and question.get("domain") != domain:
                    continue
                if skill and question.get("skill") != skill:
                    continue
                question_id = str(question.get("question_id") or id(question))
                if question_id in seen:
                    continue
                seen.add(question_id)
                pool.append(dict(question))

    rng.shuffle(pool)
    chosen = pool[:count]
    for number, question in enumerate(chosen, start=1):
        question["id"] = number
    return chosen
