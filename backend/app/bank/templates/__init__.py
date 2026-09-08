"""Registry of every question template.

Add a template by writing a :class:`~.base.Template` subclass in one of the
domain modules and appending it to that module's ``TEMPLATES`` list.
"""

from __future__ import annotations

from typing import Sequence

from .base import Question, Template, TemplateError
from . import advanced_math, algebra, data_analysis, geometry

TEMPLATES: list[Template] = [
    *algebra.TEMPLATES,
    *advanced_math.TEMPLATES,
    *data_analysis.TEMPLATES,
    *geometry.TEMPLATES,
]

BY_KEY: dict[str, Template] = {template.key: template for template in TEMPLATES}


def templates_for(
    qtype: str,
    difficulty: str,
    skills: Sequence[str] = (),
    templates: Sequence[Template] | None = None,
) -> list[Template]:
    """Every template that produces this type/difficulty, on one of ``skills``.

    An empty ``skills`` means any skill will do.
    """
    return [
        template
        for template in (TEMPLATES if templates is None else templates)
        if template.supports(qtype, difficulty) and (not skills or template.skill in skills)
    ]


def supports(skills: tuple[str, ...], qtype: str, difficulty: str) -> bool:
    """Whether some template can build exactly this combination."""
    return bool(templates_for(qtype, difficulty, skills))


__all__ = [
    "TEMPLATES",
    "BY_KEY",
    "Question",
    "Template",
    "TemplateError",
    "supports",
    "templates_for",
]
