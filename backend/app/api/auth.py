"""Registration, login and the current session."""

from __future__ import annotations

from functools import wraps

from flask import Blueprint, current_app, g, jsonify, request

from ..db import get_db
from ..services import accounts
from .errors import error_response

bp = Blueprint("auth", __name__, url_prefix="/api/auth")

STATUS_FOR_CODE = {
    "email_taken": 409,
    "invalid_credentials": 401,
    "account_disabled": 403,
    "validation_failed": 422,
    "user_not_found": 404,
}


def _iterations() -> int:
    return current_app.config["PASSWORD_ITERATIONS"]


def bearer_token() -> str:
    header = request.headers.get("Authorization", "")
    return header[7:].strip() if header.lower().startswith("bearer ") else ""


def login_required(view):
    """Reject the request unless it carries a valid session token."""

    @wraps(view)
    def wrapper(*args, **kwargs):
        user = accounts.user_for_token(get_db(), bearer_token())
        if user is None:
            return error_response(401, "not_authenticated", "Please sign in again.")
        g.current_user = user
        return view(*args, **kwargs)

    return wrapper


@bp.post("/register")
def register():
    payload = request.get_json(silent=True) or {}
    db = get_db()

    user = accounts.register(
        db,
        email=payload.get("email", ""),
        username=payload.get("username", ""),
        password=payload.get("password", ""),
        iterations=_iterations(),
    )
    return jsonify({"token": accounts.start_session(db, user.id), "user": user.to_dict()}), 201


@bp.post("/login")
def login():
    payload = request.get_json(silent=True) or {}
    db = get_db()

    user = accounts.authenticate(
        db,
        email=payload.get("email", ""),
        password=payload.get("password", ""),
        iterations=_iterations(),
    )
    return jsonify({"token": accounts.start_session(db, user.id), "user": user.to_dict()})


@bp.post("/logout")
@login_required
def logout():
    accounts.end_session(get_db(), bearer_token())
    return "", 204


@bp.get("/me")
@login_required
def me():
    return jsonify({"user": g.current_user.to_dict()})


@bp.errorhandler(accounts.AccountError)
def handle_account_error(exc: accounts.AccountError):
    return error_response(STATUS_FOR_CODE.get(exc.code, 400), exc.code, str(exc))
