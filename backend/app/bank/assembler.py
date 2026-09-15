"""Assembles bundles (module 1 + both module 2 variants) from a pool of questions.

A module is planned first: the blueprint in :mod:`.blueprint` says how many
questions each subtopic gets, which difficulty band each question number falls
in, and how many are grid-ins. The plan is a list of :class:`Slot` objects — one
per question — and the pool is then asked for a question matching each slot.

Used by both the importer and the generator so a bank built either way has the
same shape.
"""

from __future__ import annotations

import copy
import random
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from typing import Any, Callable, Iterable, Mapping, Sequence

from . import blueprint as bp
from . import taxonomy
from .ordering import exam_order

Question = dict[str, Any]

#: A callback saying whether a (skills, type, difficulty) combination can be
#: filled at all — by a template, or by what is left in an imported pool.
Supports = Callable[[tuple[str, ...], str, str], bool]

DEFAULT_MODULE_SIZE = bp.QUESTIONS_PER_MODULE
DEFAULT_SPR_COUNT = bp.STUDENT_RESPONSE_PER_MODULE

#: When a difficulty runs dry everywhere, borrow from the closest one instead
#: of failing. Topic gives way first: the difficulty bands and the grid-in
#: count are exact in ``SAT test structure/``, the subtopic counts are "~".
DIFFICULTY_FALLBACK = {
    "Easy": ("Medium", "Hard"),
    "Medium": ("Easy", "Hard"),
    "Hard": ("Medium", "Easy"),
}

#: How many random topic splits to try before settling for a plan that needs
#: fallbacks.
PLAN_ATTEMPTS = 40


class AssemblyError(RuntimeError):
    """Raised when the pool cannot cover the requested bundles."""


@dataclass(frozen=True)
class Slot:
    """One question's place in a module: what it should be about and look like.

    ``skills`` lists the blueprint skills that satisfy the slot; empty means any.
    """

    skills: tuple[str, ...]
    qtype: str
    difficulty: str

    @classmethod
    def any(cls, qtype: str, difficulty: str) -> "Slot":
        return cls((), qtype, difficulty)

    @property
    def domain(self) -> str | None:
        """The content domain the slot's skills belong to; None means any."""
        for skill in self.skills:
            domain = taxonomy.domain_of(skill)
            if domain is not None:
                return domain.name
        return None

    def accepts(self, question: Mapping[str, Any]) -> bool:
        """Whether the question is on topic. Unlabelled questions fit anywhere."""
        skill = question.get("skill")
        return not self.skills or skill is None or skill in self.skills

    def in_domain(self, question: Mapping[str, Any]) -> bool:
        """Whether the question is at least from the same content domain."""
        domain = self.domain
        if domain is None or question.get("domain") is None:
            return True
        return question.get("domain") == domain


def fallbacks(qtype: str, difficulty: str) -> list[tuple[str, str]]:
    """Type/difficulty combinations to try, best first."""
    other_type = "SPR" if qtype == "MCQ" else "MCQ"
    difficulties = (difficulty, *DIFFICULTY_FALLBACK.get(difficulty, ()))
    return [(qtype, level) for level in difficulties] + [
        (other_type, level) for level in difficulties
    ]


@dataclass(frozen=True)
class ModuleSpec:
    """One module's blueprint, ready to be planned."""

    blueprint: bp.ModuleBlueprint

    @property
    def size(self) -> int:
        return self.blueprint.size

    @property
    def spr_count(self) -> int:
        return self.blueprint.spr_count

    @property
    def mcq_count(self) -> int:
        return self.blueprint.mcq_count

    def requirements(self) -> Counter[tuple[str, str]]:
        """Counts keyed by ``(type, difficulty)``.

        Grid-ins are spread across the difficulty bands in proportion to the
        band sizes; multiple choice takes the rest of each band.
        """
        bands = self.blueprint.difficulty_counts()
        spr = bp._largest_remainder(bands, min(self.spr_count, self.size))

        counts: Counter[tuple[str, str]] = Counter()
        for difficulty, total in bands.items():
            if spr[difficulty]:
                counts[("SPR", difficulty)] += spr[difficulty]
            if total - spr[difficulty]:
                counts[("MCQ", difficulty)] += total - spr[difficulty]
        return counts

    def plan(self, rng: random.Random, supports: Supports | None = None) -> list[Slot]:
        """One slot per question, pairing topics with types and difficulties.

        ``supports`` lets the planner avoid combinations nothing can fill; if a
        few random attempts still leave some, the last attempt is returned and
        the pool's fallbacks take over for those slots.
        """
        pairs = self.requirements()
        units: list[tuple[str, ...]] = []
        for _ in range(PLAN_ATTEMPTS):
            counts = self.blueprint.resolve_topics(rng)
            units = [topic.skills for topic, count in counts.items() for _ in range(count)]
            slots = _pair_up(units, pairs, rng, supports, strict=True)
            if slots is not None:
                return slots
        return _pair_up(units, pairs, rng, supports, strict=False) or []


def _pair_up(
    units: Sequence[tuple[str, ...]],
    pairs: Counter[tuple[str, str]],
    rng: random.Random,
    supports: Supports | None,
    *,
    strict: bool,
) -> list[Slot] | None:
    """Give every topic unit a (type, difficulty) pair, most constrained first."""
    remaining = Counter(pairs)

    def fits(skills: tuple[str, ...], pair: tuple[str, str]) -> bool:
        return supports is None or supports(skills, *pair)

    order = list(units)
    rng.shuffle(order)
    order.sort(key=lambda skills: sum(1 for pair in remaining if fits(skills, pair)))

    slots: list[Slot] = []
    for skills in order:
        options = [pair for pair, count in remaining.items() if count and fits(skills, pair)]
        if not options:
            if strict:
                return None
            options = [pair for pair, count in remaining.items() if count]
        weights = [remaining[pair] for pair in options]
        qtype, difficulty = rng.choices(options, weights=weights)[0]
        remaining[(qtype, difficulty)] -= 1
        slots.append(Slot(skills, qtype, difficulty))

    rng.shuffle(slots)
    return slots


@dataclass(frozen=True)
class BundleSpec:
    """The three modules that make up one test of one section."""

    module_1: ModuleSpec = field(default_factory=lambda: ModuleSpec(bp.MODULE_1))
    module_2_higher: ModuleSpec = field(default_factory=lambda: ModuleSpec(bp.MODULE_2_HIGHER))
    module_2_lower: ModuleSpec = field(default_factory=lambda: ModuleSpec(bp.MODULE_2_LOWER))

    @classmethod
    def for_section(cls, section: str | None = None) -> "BundleSpec":
        """The full-size modules of a section, the math ones by default."""
        module_1, higher, lower = bp.modules_for(section)
        return cls(ModuleSpec(module_1), ModuleSpec(higher), ModuleSpec(lower))

    @property
    def section(self) -> str:
        return self.module_1.blueprint.section_key

    def modules(self) -> dict[str, ModuleSpec]:
        return {
            "module_1": self.module_1,
            "module_2_HIGHER": self.module_2_higher,
            "module_2_LOWER": self.module_2_lower,
        }

    @property
    def size(self) -> int:
        return sum(spec.size for spec in self.modules().values())

    def requirements(self) -> Counter[tuple[str, str]]:
        total: Counter[tuple[str, str]] = Counter()
        for spec in self.modules().values():
            total.update(spec.requirements())
        return total

    def plan(self, rng: random.Random, supports: Supports | None = None) -> dict[str, list[Slot]]:
        return {key: spec.plan(rng, supports) for key, spec in self.modules().items()}


def default_spec(
    size: int | None = None, spr_count: int | None = None, section: str | None = None
) -> BundleSpec:
    """A bundle spec for ``section`` with a custom module size, keeping the blueprint's proportions.

    A size or grid-in count left out is the section's own.
    """
    module_1, higher, lower = bp.modules_for(section)
    if size is None:
        size = module_1.size
    if spr_count is None:
        spr_count = module_1.spr_count if size == module_1.size else min(module_1.spr_count, size)
    return BundleSpec(
        module_1=ModuleSpec(module_1.scaled(size, spr_count)),
        module_2_higher=ModuleSpec(higher.scaled(size, spr_count)),
        module_2_lower=ModuleSpec(lower.scaled(size, spr_count)),
    )


class QuestionPool:
    """Draws questions by topic, type and difficulty, without repeats."""

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

    def supports(self, skills: tuple[str, ...], qtype: str, difficulty: str) -> bool:
        """Whether something on topic is left for exactly this type and difficulty."""
        slot = Slot(skills, qtype, difficulty)
        return any(slot.accepts(question) for question in self._buckets[(qtype, difficulty)])

    def draw(self, slot: Slot, count: int = 1) -> list[Question]:
        """Take ``count`` questions for ``slot``.

        Questions of the exact type and difficulty come first — on topic, then
        from the same content domain, then any topic — so a module keeps its
        difficulty bands and its grid-in count for as long as the pool has
        anything at that difficulty at all. Only when it has not do the
        neighbouring difficulties and the other type come in, in the same
        order, so a thin or unlabelled pool still fills up.
        """
        taken: list[Question] = []
        for key in fallbacks(slot.qtype, slot.difficulty):
            for matches in (slot.accepts, slot.in_domain, None):
                bucket = self._buckets[key]
                index = 0
                while index < len(bucket) and len(taken) < count:
                    if matches is None or matches(bucket[index]):
                        taken.append(bucket.pop(index))
                    else:
                        index += 1
                if len(taken) == count:
                    return taken

        raise AssemblyError(
            f"pool ran out while drawing {count} {slot.difficulty} {slot.qtype} question(s) "
            f"(got {len(taken)}); add more questions or lower --module-size"
        )


def assemble_bundle(
    pool: QuestionPool,
    plan: Mapping[str, Sequence[Slot]],
    test_id: str,
    section: str | None = None,
) -> dict[str, Any]:
    """Draw one full bundle. Questions are deep-copied so bundles stay independent.

    Each module is stored the way the exam runs it — easy first and hard last,
    or grouped by domain for Reading and Writing — so the bank, the papers in
    ``answer-keys/`` and the served module all number the questions the same.
    """
    section = taxonomy.section_of(section).key
    bundle: dict[str, Any] = {"test_id": test_id, "section": section}
    for key, slots in plan.items():
        questions = [question for slot in slots for question in pool.draw(slot)]
        bundle[key] = exam_order((copy.deepcopy(question) for question in questions), section)
    return bundle


def assemble_bank(
    questions: Sequence[Question],
    *,
    bundles: int = 1,
    spec: BundleSpec | None = None,
    rng: random.Random | None = None,
    test_id_prefix: str = "sat-mock",
) -> list[dict[str, Any]]:
    """Build ``bundles`` tests out of ``questions``, for the section of ``spec``."""
    spec = spec or BundleSpec()
    rng = rng or random.Random()
    needed = spec.size * bundles
    if len(questions) < needed:
        raise AssemblyError(
            f"need {needed} questions for {bundles} bundle(s), pool has {len(questions)}"
        )

    pool = QuestionPool(questions, rng)
    return [
        assemble_bundle(
            pool, spec.plan(rng, pool.supports), f"{test_id_prefix}-{index:02d}", spec.section
        )
        for index in range(1, bundles + 1)
    ]
