"""Friends and messages, for the signed-in student."""

from __future__ import annotations

from flask import Blueprint, g, jsonify, request

from ..db import get_db
from ..services import accounts, social
from .auth import login_required
from .errors import error_response

bp = Blueprint("social", __name__, url_prefix="/api")


@bp.get("/friends")
@login_required
def friends():
    return jsonify(social.overview(get_db(), g.current_user.id))


@bp.post("/friends/requests")
@login_required
def send_friend_request():
    payload = request.get_json(silent=True) or {}
    try:
        other_id = int(payload["user_id"])
    except (KeyError, TypeError, ValueError):
        return error_response(422, "validation_failed", "user_id is required.")
    return jsonify(social.send_request(get_db(), g.current_user.id, other_id)), 201


@bp.post("/friends/requests/<int:request_id>/accept")
@login_required
def accept_friend_request(request_id: int):
    return jsonify(social.accept_request(get_db(), g.current_user.id, request_id))


@bp.delete("/friends/requests/<int:request_id>")
@login_required
def remove_friend_request(request_id: int):
    social.remove_request(get_db(), g.current_user.id, request_id)
    return "", 204


@bp.delete("/friends/<int:user_id>")
@login_required
def unfriend(user_id: int):
    social.unfriend(get_db(), g.current_user.id, user_id)
    return "", 204


@bp.get("/messages")
@login_required
def conversations():
    db = get_db()
    return jsonify(
        {
            "conversations": social.conversations(db, g.current_user.id),
            "unread": social.unread_count(db, g.current_user.id),
        }
    )


@bp.get("/messages/<int:user_id>")
@login_required
def thread(user_id: int):
    return jsonify(social.thread(get_db(), g.current_user.id, user_id))


@bp.post("/messages/<int:user_id>")
@login_required
def send_message(user_id: int):
    payload = request.get_json(silent=True) or {}
    message = social.send_message(get_db(), g.current_user.id, user_id, payload.get("body", ""))
    return jsonify({"message": message}), 201


@bp.errorhandler(accounts.AccountError)
def handle_social_error(exc: accounts.AccountError):
    status = {"not_allowed": 409, "user_not_found": 404, "validation_failed": 422}.get(exc.code, 400)
    return error_response(status, exc.code, str(exc))
