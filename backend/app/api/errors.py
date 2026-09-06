"""JSON error helpers shared by the API blueprint."""

from __future__ import annotations

from typing import Any

from flask import jsonify


def error_response(status: int, code: str, message: str, **extra: Any):
    """Build the single error envelope every endpoint returns."""
    payload: dict[str, Any] = {"error": {"code": code, "message": message}}
    if extra:
        payload["error"].update(extra)
    return jsonify(payload), status
