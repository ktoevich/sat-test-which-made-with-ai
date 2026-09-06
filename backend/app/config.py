"""Application configuration objects.

Values are read from environment variables so that the same code runs in
development, testing and production without edits.
"""

from __future__ import annotations

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent


def _env_bool(name: str, default: bool = False) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


class BaseConfig:
    """Settings shared by every environment."""

    # Absolute path to the JSON file holding the pre-generated test bundles.
    QUESTION_BANK_PATH = Path(
        os.environ.get("QUESTION_BANK_PATH", BASE_DIR / "data" / "tests_bundle_cache.json")
    )

    # SQLite file used when no database URL is configured.
    DATABASE_PATH = Path(os.environ.get("DATABASE_PATH", BASE_DIR / "data" / "app.db"))

    # A postgres:// URL takes precedence over DATABASE_PATH. Managed Postgres
    # add-ons usually expose one of these names; the pooled URL is the right one
    # for serverless, where every request opens its own connection.
    DATABASE_URL = (
        os.environ.get("DATABASE_URL")
        or os.environ.get("POSTGRES_URL")
        or os.environ.get("POSTGRES_PRISMA_URL")
        or ""
    )

    # PBKDF2 rounds for password hashing. Raise as hardware gets faster.
    PASSWORD_ITERATIONS = int(os.environ.get("PASSWORD_ITERATIONS", 600_000))

    # Origins allowed to call the API from a browser.
    CORS_ORIGINS = [
        origin.strip()
        for origin in os.environ.get("CORS_ORIGINS", "*").split(",")
        if origin.strip()
    ]

    # Directory with the static frontend; served by Flask in development so the
    # whole app can run from a single process.
    FRONTEND_DIR = Path(os.environ.get("FRONTEND_DIR", BASE_DIR.parent / "frontend"))
    SERVE_FRONTEND = _env_bool("SERVE_FRONTEND", True)

    JSON_SORT_KEYS = False
    TESTING = False


class DevelopmentConfig(BaseConfig):
    DEBUG = True


class ProductionConfig(BaseConfig):
    DEBUG = False
    # In production the frontend is served as static files by the CDN or web
    # server, not by Flask. Set SERVE_FRONTEND=1 to override.
    SERVE_FRONTEND = _env_bool("SERVE_FRONTEND", False)


class TestingConfig(BaseConfig):
    DEBUG = False
    TESTING = True
    SERVE_FRONTEND = False
    DATABASE_URL = ""
    # Tests point DATABASE_PATH at a temp file; an in-memory SQLite database
    # would be a different, empty database for every connection.
    # Hashing is deliberately slow; tests would crawl at the production setting.
    PASSWORD_ITERATIONS = 1_000


CONFIGS = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
    "testing": TestingConfig,
}


def get_config(name: str | None = None) -> type[BaseConfig]:
    """Resolve a config class by name, falling back to ``FLASK_ENV``."""
    key = (name or os.environ.get("FLASK_ENV") or "development").lower()
    return CONFIGS.get(key, DevelopmentConfig)
