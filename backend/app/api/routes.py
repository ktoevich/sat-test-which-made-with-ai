"""HTTP endpoints that hand exam modules to the frontend."""

from __future__ import annotations

from flask import Blueprint, current_app, jsonify, request

from ..services import QuestionBankError, build_module
from .errors import error_response

bp = Blueprint("api", __name__, url_prefix="/api")


def _bank():
    return current_app.extensions["question_bank"]


@bp.get("/health")
def health():
    """Liveness probe that also reports whether any test is ready to serve."""
    bank = _bank()
    return jsonify({"status": "ok", "tests_available": bank.count()})


@bp.get("/tests/module-1")
def module_1():
    """Start an attempt: pick a random bundle and return its first module."""
    bank = _bank()
    if bank.is_empty:
        return error_response(
            503, "bank_empty", "No generated tests are available yet. Please try again later."
        )

    bundle = bank.random_bundle()
    questions = build_module(bank.module_1(bundle))
    return jsonify({"test_id": bundle["test_id"], "module": 1, "questions": questions})


@bp.get("/tests/module-2")
def module_2():
    """Return the adaptive second module for an attempt already in progress."""
    bank = _bank()
    if bank.is_empty:
        return error_response(
            503, "bank_empty", "No generated tests are available yet. Please try again later."
        )

    test_id = request.args.get("test_id")
    target = request.args.get("target", "HIGHER")

    bundle = bank.get_bundle(test_id)
    if bundle is None:
        return error_response(
            404,
            "test_not_found",
            f"Test {test_id!r} is no longer available. Please start a new attempt.",
        )

    questions = build_module(bank.module_2(bundle, target))
    return jsonify({"test_id": bundle["test_id"], "module": 2, "questions": questions})


@bp.errorhandler(QuestionBankError)
def handle_bank_error(exc: QuestionBankError):
    return error_response(422, "invalid_request", str(exc))


@bp.app_errorhandler(404)
def handle_not_found(exc):
    """Answer unknown API paths with JSON; leave the rest to the static handler."""
    if request.path.startswith("/api/"):
        return error_response(404, "not_found", f"No API endpoint at {request.path}")
    return exc.get_response()
