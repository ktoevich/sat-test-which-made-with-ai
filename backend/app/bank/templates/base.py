"""Base class and helpers shared by every question template."""

from __future__ import annotations

import hashlib
import json
import random
from abc import ABC, abstractmethod
from itertools import chain
from typing import Any, Iterable, Iterator, Sequence

from ..latex import number as _format

Question = dict[str, Any]

ALL_DIFFICULTIES = ("Easy", "Medium", "Hard")
OPTION_LETTERS = ("A", "B", "C", "D")


class TemplateError(RuntimeError):
    """Raised when a template cannot build a valid question."""


#: Fields that make one question different from another.
IDENTITY_FIELDS = ("text", "options", "answer", "image")


def fingerprint(question: dict[str, Any]) -> str:
    """Short, stable id covering everything that distinguishes a question.

    The prompt alone is not enough: a template can reuse one wording and vary
    only the figure, so the options and the image have to be part of the id.
    """
    payload = json.dumps(
        {field: question.get(field) for field in IDENTITY_FIELDS},
        sort_keys=True,
        ensure_ascii=False,
    )
    return hashlib.sha1(payload.encode()).hexdigest()[:8]


#: Offsets used to pad numeric distractors when the plausible ones collide.
DEFAULT_DELTAS = (1, -1, 2, -2, 3, -3, 5, -5, 10, -10, 20, -20)


def numeric_variants(
    value: float, *, deltas: Sequence[int] = DEFAULT_DELTAS, digits: int | None = None
) -> Iterator[str]:
    """Nearby numbers, as a last-resort supply of distinct distractors."""
    for delta in deltas:
        candidate = value + delta
        yield _format(round(candidate, digits) if digits is not None else candidate)


def pick_distractors(
    correct: str,
    candidates: Iterable[str],
    count: int = 3,
    pad: Iterable[str] = (),
) -> list[str]:
    """Take the first ``count`` distinct candidates that differ from the answer.

    ``pad`` is drawn from only after ``candidates`` runs out, so the plausible,
    template-specific wrong answers always come first.
    """
    seen = {correct}
    chosen: list[str] = []
    for candidate in chain(candidates, pad):
        if candidate in seen:
            continue
        seen.add(candidate)
        chosen.append(candidate)
        if len(chosen) == count:
            return chosen
    raise TemplateError(f"only {len(chosen)} distinct distractors for answer {correct!r}")


class Template(ABC):
    """Builds one family of questions across the three difficulty levels."""

    key: str = ""
    domain: str = ""
    skill: str = ""
    types: tuple[str, ...] = ("MCQ",)
    difficulties: tuple[str, ...] = ALL_DIFFICULTIES

    def supports(self, qtype: str, difficulty: str) -> bool:
        return qtype in self.types and difficulty in self.difficulties

    @abstractmethod
    def build(self, rng: random.Random, qtype: str, difficulty: str) -> Question:
        """Return one question. Implementations use :meth:`mcq` / :meth:`spr`."""

    # -- construction helpers ------------------------------------------

    def mcq(
        self,
        *,
        text: str,
        correct: str,
        distractors: Sequence[str],
        rationale: str,
        difficulty: str,
        rng: random.Random,
        image: Any = None,
    ) -> Question:
        choices = [correct, *distractors[: len(OPTION_LETTERS) - 1]]
        if len(choices) != len(OPTION_LETTERS):
            raise TemplateError(f"{self.key}: expected {len(OPTION_LETTERS)} choices")

        rng.shuffle(choices)
        options = [f"{letter}) {body}" for letter, body in zip(OPTION_LETTERS, choices)]
        answer = OPTION_LETTERS[choices.index(correct)]
        return self._question(
            text=text,
            answer=answer,
            qtype="MCQ",
            difficulty=difficulty,
            rationale=rationale,
            image=image,
            options=options,
        )

    def spr(
        self,
        *,
        text: str,
        answer: str,
        rationale: str,
        difficulty: str,
        image: Any = None,
    ) -> Question:
        return self._question(
            text=text,
            answer=str(answer),
            qtype="SPR",
            difficulty=difficulty,
            rationale=rationale,
            image=image,
        )

    def _question(
        self,
        *,
        text: str,
        answer: str,
        qtype: str,
        difficulty: str,
        rationale: str,
        image: Any,
        options: list[str] | None = None,
    ) -> Question:
        question: Question = {
            "domain": self.domain,
            "skill": self.skill,
            "difficulty": difficulty,
            "type": qtype,
            "text": text,
            "answer": answer,
            "rationale": rationale,
            "image": image,
            "template": self.key,
        }
        if options is not None:
            question["options"] = options

        # The id depends on the finished question, so it is filled in last.
        return {"question_id": fingerprint(question), **question}


def nonzero(rng: random.Random, low: int, high: int) -> int:
    """A random integer in ``[low, high]``, never 0."""
    value = 0
    while value == 0:
        value = rng.randint(low, high)
    return value
