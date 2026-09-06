"""Registry of every question template.

Add a template by writing a :class:`~.base.Template` subclass in one of the
domain modules and appending it to that module's ``TEMPLATES`` list.
"""

from __future__ import annotations

from .base import Question, Template, TemplateError
from . import advanced_math, algebra, data_analysis, geometry

TEMPLATES: list[Template] = [
    *algebra.TEMPLATES,
    *advanced_math.TEMPLATES,
    *data_analysis.TEMPLATES,
    *geometry.TEMPLATES,
]

BY_KEY: dict[str, Template] = {template.key: template for template in TEMPLATES}


def templates_for(qtype: str, difficulty: str) -> list[Template]:
    """Every template that can produce this type/difficulty combination."""
    return [template for template in TEMPLATES if template.supports(qtype, difficulty)]


__all__ = ["TEMPLATES", "BY_KEY", "Question", "Template", "TemplateError", "templates_for"]
