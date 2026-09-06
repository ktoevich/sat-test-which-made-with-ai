"""Application factory for the SAT practice backend."""

from __future__ import annotations

import logging
from pathlib import Path

from flask import Flask, send_from_directory

from . import db
from .api import BLUEPRINTS
from .config import BaseConfig, get_config
from .extensions import cors
from .services import QuestionBank


def create_app(config_name: str | None = None, **overrides) -> Flask:
    """Build and configure a Flask application instance.

    ``config_name`` selects one of ``development`` / ``production`` / ``testing``;
    ``overrides`` lets tests point at a different question bank, and so on.
    """
    app = Flask(__name__, static_folder=None)
    app.config.from_object(get_config(config_name))
    app.config.update(overrides)

    _configure_logging(app)
    cors.init_app(app, resources={r"/api/*": {"origins": app.config["CORS_ORIGINS"]}})

    app.extensions["question_bank"] = QuestionBank(app.config["QUESTION_BANK_PATH"])
    db.init_app(app)

    for blueprint in BLUEPRINTS:
        app.register_blueprint(blueprint)

    if app.config.get("SERVE_FRONTEND"):
        _register_frontend(app, Path(app.config["FRONTEND_DIR"]))

    return app


def _configure_logging(app: Flask) -> None:
    level = logging.DEBUG if app.config.get("DEBUG") else logging.INFO
    logging.basicConfig(level=level, format="%(asctime)s %(levelname)-8s %(name)s: %(message)s")
    app.logger.setLevel(level)


def _register_frontend(app: Flask, frontend_dir: Path) -> None:
    """Serve the static frontend so the whole app runs from one process in dev."""
    if not frontend_dir.is_dir():
        app.logger.warning("Frontend directory %s not found; serving API only", frontend_dir)
        return

    @app.get("/")
    def index():
        return send_from_directory(frontend_dir, "index.html")

    @app.get("/<path:filename>")
    def static_files(filename: str):
        return send_from_directory(frontend_dir, filename)


__all__ = ["create_app", "BaseConfig"]
