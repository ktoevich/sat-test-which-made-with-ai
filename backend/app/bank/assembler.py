"""Assembles bundles (module 1 + both module 2 variants) from a pool of questions.

Used by both the importer and the generator so a bank built either way has the
same shape and difficulty mix.
"""

from __future__ import annotations

import copy
import random
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from typing import Any, Iterable, Mapping, Sequence

Question = dict[str, Any]

#: Digital SAT math modules are 22 questions, roughly a quarter of them grid-ins.
DEFAULT_MODULE_SIZE = 22
DEFAULT_SPR_COUNT = 6

#: Difficulty mix per module. Module 2 skews with the adaptive target.
MODULE_1_MIX = {"Easy": 0.35, "Medium": 0.40, "Hard": 0.25}
MODULE_2_HIGHER_MIX = {"Easy": 0.15, "Medium": 0.35, "Hard": 0.50}
MODULE_2_LOWER_MIX = {"Easy": 0.50, "Medium": 0.35, "Hard": 0.15}

#: When a difficulty runs dry, borrow from the closest one instead of failing.
DIFFICULTY_FALLBACK = {
    "Easy": ("Medium", "Hard"),
    "Medium": ("Easy", "Hard"),
    "Hard": ("Medium", "Easy"),
}


class AssemblyError(RuntimeError):
    """Raised when the pool cannot cover the requested bundles."""


@dataclass(frozen=True)
class ModuleSpec:
    """How many questions of each type and difficulty a module needs."""

    mix: Mapping[str, float]
    size: int = DEFAULT_MODULE_SIZE
    spr_count: int = DEFAULT_SPR_COUNT

    @property
    def mcq_count(self) -> int:
        return max(0, self.size - self.spr_count)

    def requirements(self) -> Counter[tuple[str, str]]:
        """Counts keyed by ``(type, difficulty)``."""
        counts: Counter[tuple[str, str]] = Counter()
        for qtype, total in (("MCQ", self.mcq_count), ("SPR", min(self.spr_count, self.size))):
            for difficulty, amount in _split_by_mix(total, self.mix).items():
                if amount:
                    counts[(qtype, difficulty)] += amount
        return counts


@dataclass(frozen=True)
class BundleSpec:
    """The three modules that make up one test."""

    module_1: ModuleSpec = field(default_factory=lambda: ModuleSpec(MODULE_1_MIX))
    module_2_higher: ModuleSpec = field(default_factory=lambda: ModuleSpec(MODULE_2_HIGHER_MIX))
    module_2_lower: ModuleSpec = field(default_factory=lambda: ModuleSpec(MODULE_2_LOWER_MIX))

    def modules(self) -> dict[str, ModuleSpec]:
        return {
            "module_1": self.module_1,
            "module_2_HIGHER": self.module_2_higher,
            "module_2_LOWER": self.module_2_lower,
        }

    def requirements(self) -> Counter[tuple[str, str]]:
        total: Counter[tuple[str, str]] = Counter()
        for spec in self.modules().values():
            total.update(spec.requirements())
        return total


def default_spec(size: int = DEFAULT_MODULE_SIZE, spr_count: int = DEFAULT_SPR_COUNT) -> BundleSpec:
    """A bundle spec with a custom module size, keeping the standard mixes."""
    return BundleSpec(
        module_1=ModuleSpec(MODULE_1_MIX, size, spr_count),
        module_2_higher=ModuleSpec(MODULE_2_HIGHER_MIX, size, spr_count),
        module_2_lower=ModuleSpec(MODULE_2_LOWER_MIX, size, spr_count),
    )


def _split_by_mix(total: int, mix: Mapping[str, float]) -> dict[str, int]:
    """Split ``total`` across difficulties, giving leftovers to the largest shares."""
    if total <= 0:
        return {}

    exact = {difficulty: total * share for difficulty, share in mix.items()}
    counts = {difficulty: int(value) for difficulty, value in exact.items()}

    remainder = total - sum(counts.values())
    by_fraction = sorted(exact, key=lambda key: exact[key] - counts[key], reverse=True)
    for difficulty in by_fraction[:remainder]:
        counts[difficulty] += 1
    return counts


class QuestionPool:
    """Draws questions by type and difficulty, without repeats."""

    def __init__(self, questions: Iterable[Question], rng: random.Random | None = None) -> None:
        self._rng = rng or random.Random()
        self._buckets: dict[tuple[str, str], list[Question]] = defaultdict(list)

        pool = list(questions)
        self._rng.shuffle(pool)
        for question in pool:
            key = (question.get("type", "MCQ"), question.get("difficulty", "Medium"))
            self._buckets[key].append(question)

    def __len__(self) -> int:
        return sum(len(bucket) for bucket in self._buckets.values())

    def available(self, qtype: str, difficulty: str) -> int:
        return len(self._buckets[(qtype, difficulty)])

    def draw(self, qtype: str, difficulty: str, count: int) -> list[Question]:
        """Take ``count`` questions, falling back to neighbouring difficulties,
        then to the other question type, before giving up."""
        taken: list[Question] = []
        for candidate_type, candidate_difficulty in self._preference(qtype, difficulty):
            bucket = self._buckets[(candidate_type, candidate_difficulty)]
            while bucket and len(taken) < count:
                taken.append(bucket.pop())
            if len(taken) == count:
                return taken

        raise AssemblyError(
            f"pool ran out while drawing {count} {difficulty} {qtype} questions "
            f"(got {len(taken)}); add more questions or lower --module-size"
        )

    def _preference(self, qtype: str, difficulty: str) -> list[tuple[str, str]]:
        other_type = "SPR" if qtype == "MCQ" else "MCQ"
        difficulties = (difficulty, *DIFFICULTY_FALLBACK.get(difficulty, ()))
        return [(qtype, level) for level in difficulties] + [
            (other_type, level) for level in difficulties
        ]


def assemble_bundle(pool: QuestionPool, spec: BundleSpec, test_id: str) -> dict[str, Any]:
    """Draw one full bundle. Questions are deep-copied so bundles stay independent."""
    bundle: dict[str, Any] = {"test_id": test_id}
    for key, module_spec in spec.modules().items():
        questions: list[Question] = []
        for (qtype, difficulty), count in sorted(module_spec.requirements().items()):
            questions.extend(pool.draw(qtype, difficulty, count))
        bundle[key] = [copy.deepcopy(question) for question in questions]
    return bundle


def assemble_bank(
    questions: Sequence[Question],
    *,
    bundles: int = 1,
    spec: BundleSpec | None = None,
    rng: random.Random | None = None,
    test_id_prefix: str = "sat-mock",
) -> list[dict[str, Any]]:
    """Build ``bundles`` tests out of ``questions``."""
    spec = spec or BundleSpec()
    needed = sum(spec.requirements().values()) * bundles
    if len(questions) < needed:
        raise AssemblyError(
            f"need {needed} questions for {bundles} bundle(s), pool has {len(questions)}"
        )

    pool = QuestionPool(questions, rng)
    return [
        assemble_bundle(pool, spec, f"{test_id_prefix}-{index:02d}")
        for index in range(1, bundles + 1)
    ]
