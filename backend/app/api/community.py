"""Other students: search, public profiles, the leaderboard, the platform's numbers."""

from __future__ import annotations

from flask import Blueprint, g, jsonify, request

from ..bank.taxonomy import DEFAULT_SECTION, SECTION_KEYS
from ..db import get_db
from ..services import community
from .auth import login_required
from .errors import error_response

bp = Blueprint("community", __name__, url_prefix="/api")


@bp.get("/users/search")
@login_required
def search_users():
    limit = request.args.get("limit", 8, type=int)
    return jsonify({"users": community.search_users(get_db(), request.args.get("q", ""), limit=limit)})


@bp.get("/users/<int:user_id>")
@login_required
def public_profile(user_id: int):
    profile = community.public_profile(get_db(), g.current_user.id, user_id)
    if profile is None:
        return error_response(404, "user_not_found", "That student does not exist.")
    return jsonify(profile)


@bp.get("/leaderboard")
def leaderboard():
    section = request.args.get("section", DEFAULT_SECTION)
    if section not in SECTION_KEYS:
        return error_response(422, "validation_failed", f"section must be one of {SECTION_KEYS}.")
    limit = request.args.get("limit", 20, type=int)
    return jsonify({"section": section, "leaderboard": community.leaderboard(get_db(), section=section, limit=limit)})


@bp.get("/stats")
def platform_stats():
    return jsonify(community.platform_stats(get_db()))
