"""Generates original practice questions from the templates.

Every question produced here is built from this project's own templates and
randomised parameters — nothing is copied from a third-party question bank.
"""

from __future__ import annotations

import random
from collections import Counter
from typing import Any, Sequence

from .assembler import BundleSpec, Slot, fallbacks
from .ordering import exam_order
from .templates import Template, TemplateError, supports, templates_for

Question = dict[str, Any]

#: How many times to retry a template before giving up on a slot.
MAX_ATTEMPTS_PER_QUESTION = 40


class GenerationError(RuntimeError):
    """Raised when no template can fill a requested slot."""


def generate_questions(
    slots: Sequence[Slot],
    *,
    rng: random.Random | None = None,
    templates: Sequence[Template] | None = None,
) -> list[Question]:
    """Build one question per slot, in the same order.

    Duplicates are rejected by fingerprint, so a bank never repeats a question.
    Templates are rotated so no single one dominates a skill.
    """
    rng = rng or random.Random()
    questions: list[Question] = []
    seen: set[str] = set()
    by_template: Counter[str] = Counter()

    for slot in slots:
        question = _build_one(slot, rng, seen, by_template, templates)
        by_template[question["template"]] += 1
        questions.append(question)
    return questions


def _candidates(
    slot: Slot, templates: Sequence[Template] | None
) -> tuple[list[Template], str, str]:
    """Templates for the slot, relaxing difficulty and then type when needed."""
    for qtype, difficulty in fallbacks(slot.qtype, slot.difficulty):
        found = templates_for(qtype, difficulty, slot.skills, templates)
        if found:
            return found, qtype, difficulty

    about = f"about {', '.join(slot.skills)} " if slot.skills else ""
    raise GenerationError(
        f"no template produces {slot.difficulty} {slot.qtype} questions {about}"
        "or anything close to it"
    )


def _select_template(
    candidates: Sequence[Template], rng: random.Random, by_template: Counter[str]
) -> Template:
    """The least-used template, with ties broken at random."""
    fewest = min(by_template[template.key] for template in candidates)
    return rng.choice([template for template in candidates if by_template[template.key] == fewest])


def _build_one(
    slot: Slot,
    rng: random.Random,
    seen: set[str],
    by_template: Counter[str],
    templates: Sequence[Template] | None,
) -> Question:
    candidates, qtype, difficulty = _candidates(slot, templates)
    last_error: Exception | None = None

    for _ in range(MAX_ATTEMPTS_PER_QUESTION):
        template = _select_template(candidates, rng, by_template)
        try:
            question = template.build(rng, qtype, difficulty)
        except TemplateError as error:  # a bad random draw; try again
            last_error = error
            continue

        if question["question_id"] in seen:
            continue
        seen.add(question["question_id"])
        return question

    raise GenerationError(
        f"could not build a unique {difficulty} {qtype} question after "
        f"{MAX_ATTEMPTS_PER_QUESTION} attempts"
        + (f" (last error: {last_error})" if last_error else "")
    )


def generate_bank(
    *,
    bundles: int = 1,
    spec: BundleSpec | None = None,
    rng: random.Random | None = None,
    test_id_prefix: str = "sat-generated",
) -> list[dict[str, Any]]:
    """Plan ``bundles`` tests from the blueprint and build a question for every slot."""
    rng = rng or random.Random()
    spec = spec or BundleSpec()

    plans = [spec.plan(rng, supports) for _ in range(bundles)]
    slots = [slot for plan in plans for module in plan.values() for slot in module]
    questions = iter(generate_questions(slots, rng=rng))

    bank: list[dict[str, Any]] = []
    for index, plan in enumerate(plans, start=1):
        bundle: dict[str, Any] = {"test_id": f"{test_id_prefix}-{index:02d}"}
        for key, module in plan.items():
            bundle[key] = exam_order(next(questions) for _ in module)
        bank.append(bundle)
    return bank
