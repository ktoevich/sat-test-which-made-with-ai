"""Generates original practice questions from the templates.

Every question produced here is built from this project's own templates and
randomised parameters — nothing is copied from a third-party question bank.
"""

from __future__ import annotations

import random
from collections import Counter
from typing import Any, Sequence

from . import taxonomy
from .assembler import BundleSpec, assemble_bank
from .templates import Template, TemplateError, templates_for

Question = dict[str, Any]

#: How many times to retry a template before giving up on a slot.
MAX_ATTEMPTS_PER_QUESTION = 40


class GenerationError(RuntimeError):
    """Raised when no template can fill a requested slot."""


def generate_questions(
    requirements: Counter[tuple[str, str]],
    *,
    rng: random.Random | None = None,
    templates: Sequence[Template] | None = None,
) -> list[Question]:
    """Build one question per unit in ``requirements``, keyed by (type, difficulty).

    Duplicates are rejected by fingerprint, so a bank never repeats a question.
    """
    rng = rng or random.Random()
    questions: list[Question] = []
    seen: set[str] = set()

    # Aim at the published domain weighting (35/35/15/15) across the whole batch.
    targets = taxonomy.target_counts(sum(requirements.values()))
    by_domain: Counter[str] = Counter()
    by_template: Counter[str] = Counter()

    for (qtype, difficulty), count in sorted(requirements.items()):
        candidates = list(templates) if templates else templates_for(qtype, difficulty)
        candidates = [t for t in candidates if t.supports(qtype, difficulty)]
        if not candidates:
            raise GenerationError(f"no template produces {difficulty} {qtype} questions")

        for _ in range(count):
            question = _build_one(
                candidates, qtype, difficulty, rng, seen, targets, by_domain, by_template
            )
            by_domain[question["domain"]] += 1
            by_template[question["template"]] += 1
            questions.append(question)

    rng.shuffle(questions)
    return questions


def _select_template(
    candidates: Sequence[Template],
    rng: random.Random,
    targets: dict[str, int],
    by_domain: Counter[str],
    by_template: Counter[str],
) -> Template:
    """Pick the domain furthest below its target, then its least-used template.

    Chasing the largest relative deficit keeps the bank close to the blueprint
    without hard-partitioning the slots, which would be impossible to fill for
    combinations only a few templates support.
    """

    def deficit(template: Template) -> float:
        target = targets.get(template.domain, 0)
        if not target:
            return float("-inf")
        return (target - by_domain[template.domain]) / target

    best = max(deficit(template) for template in candidates)
    pool = [template for template in candidates if deficit(template) >= best - 1e-9]

    fewest = min(by_template[template.key] for template in pool)
    return rng.choice([template for template in pool if by_template[template.key] == fewest])


def _build_one(
    candidates: Sequence[Template],
    qtype: str,
    difficulty: str,
    rng: random.Random,
    seen: set[str],
    targets: dict[str, int],
    by_domain: Counter[str],
    by_template: Counter[str],
) -> Question:
    last_error: Exception | None = None

    for _ in range(MAX_ATTEMPTS_PER_QUESTION):
        template = _select_template(candidates, rng, targets, by_domain, by_template)
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
    """Generate exactly enough questions for ``bundles`` tests, then assemble them."""
    rng = rng or random.Random()
    spec = spec or BundleSpec()

    requirements: Counter[tuple[str, str]] = Counter()
    for key, count in spec.requirements().items():
        requirements[key] = count * bundles

    questions = generate_questions(requirements, rng=rng)
    return assemble_bank(
        questions,
        bundles=bundles,
        spec=spec,
        rng=rng,
        test_id_prefix=test_id_prefix,
    )
