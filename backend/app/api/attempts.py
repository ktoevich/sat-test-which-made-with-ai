"""Test history for the signed-in user."""

from __future__ import annotations

from flask import Blueprint, g, jsonify, request

from ..db import get_db
from ..services import attempts as attempts_service
from .auth import login_required
from .errors import error_response

bp = Blueprint("attempts", __name__, url_prefix="/api/attempts")


@bp.get("")
@login_required
def list_attempts():
    db = get_db()
    return jsonify(
        {
            "attempts": attempts_service.list_for_user(db, g.current_user.id),
            "summary": attempts_service.summary(db, g.current_user.id),
        }
    )


@bp.post("")
@login_required
def create_attempt():
    payload = request.get_json(silent=True) or {}

    try:
        score = int(payload["score"])
        correct = int(payload["correct"])
        total = int(payload["total"])
    except (KeyError, TypeError, ValueError):
        return error_response(422, "validation_failed", "score, correct and total are required.")

    if total <= 0 or not 0 <= correct <= total:
        return error_response(422, "validation_failed", "correct must be between 0 and total.")

    details = payload.get("details")
    attempt = attempts_service.record(
        get_db(),
        user_id=g.current_user.id,
        score=score,
        correct=correct,
        total=total,
        details=details if isinstance(details, list) else [],
    )
    return jsonify({"attempt": attempt}), 201
