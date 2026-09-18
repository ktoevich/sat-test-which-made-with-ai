"""Practice by domain: a few questions from the bank, answers included for instant checking."""

from __future__ import annotations

from flask import Blueprint, current_app, jsonify, request

from ..bank.taxonomy import DEFAULT_SECTION, SECTION_KEYS, section_of
from ..services import practice
from .errors import error_response

bp = Blueprint("practice", __name__, url_prefix="/api")


@bp.get("/practice")
def practice_set():
    """``section``, ``domain`` (or ``skill``) and ``count`` pick the set."""
    bank = current_app.extensions["question_bank"]
    section = request.args.get("section", DEFAULT_SECTION)
    if section not in SECTION_KEYS:
        return error_response(422, "validation_failed", f"section must be one of {SECTION_KEYS}.")
    domain = request.args.get("domain") or None
    if domain and domain not in {d.name for d in section_of(section).domains}:
        return error_response(422, "validation_failed", f"{domain!r} is not a {section} domain.")
    if not bank.has_section(section):
        return error_response(503, "bank_empty", "No generated tests are available yet.")

    questions = practice.practice_questions(
        bank,
        section=section,
        domain=domain,
        skill=request.args.get("skill") or None,
        count=request.args.get("count", practice.DEFAULT_COUNT, type=int),
    )
    return jsonify({"section": section, "domain": domain, "questions": questions})
