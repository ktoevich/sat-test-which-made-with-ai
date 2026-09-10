"""JSON error helpers shared by the API blueprint."""

from __future__ import annotations

from typing import Any

from flask import jsonify, request
from werkzeug.exceptions import HTTPException


def error_response(status: int, code: str, message: str, **extra: Any):
    """Build the single error envelope every endpoint returns."""
    payload: dict[str, Any] = {"error": {"code": code, "message": message}}
    if extra:
        payload["error"].update(extra)
    return jsonify(payload), status


def register_error_handlers(app) -> None:
    """Translate infrastructure failures into the same JSON envelope."""
    from ..db import DatabaseUnavailable

    @app.errorhandler(Exception)
    def _unexpected(error: Exception):
        """The last resort, so a bug is never answered with a stack trace.

        Werkzeug's own 500 page carries the traceback — file paths, source
        lines, and whatever a driver put in its message, which for a failed
        connection can include the database URL. None of that belongs in a
        response. The detail goes to the log instead.
        """
        if isinstance(error, HTTPException):
            return error  # 404s and friends already say what they mean.
        app.logger.exception("Unhandled error serving %s", request.path)
        return error_response(500, "internal_error", "Something went wrong on our side.")

    @app.errorhandler(DatabaseUnavailable)
    def _database_unavailable(error: DatabaseUnavailable):
        app.logger.error("Database unavailable: %s", error)
        return error_response(
            503,
            "database_unavailable",
            "The database is not reachable. Accounts and history are unavailable.",
        )
