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


def register_error_handlers(app) -> None:
    """Translate infrastructure failures into the same JSON envelope."""
    from ..db import DatabaseUnavailable

    @app.errorhandler(DatabaseUnavailable)
    def _database_unavailable(error: DatabaseUnavailable):
        app.logger.error("Database unavailable: %s", error)
        return error_response(
            503,
            "database_unavailable",
            "The database is not reachable. Accounts and history are unavailable.",
        )
