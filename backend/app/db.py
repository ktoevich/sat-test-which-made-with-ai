"""Database access for both SQLite (local) and PostgreSQL (deployed).

Serverless hosts give you a read-only, throwaway filesystem, so a SQLite file
cannot survive there. Set ``DATABASE_URL`` (or ``POSTGRES_URL``) and the same
code talks to PostgreSQL instead.

Services use the small :class:`Database` wrapper rather than a raw DB-API
connection so one SQL dialect works on both: write ``?`` placeholders and use
:meth:`Database.insert` when you need the new row's id.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any, Mapping, Sequence

from flask import Flask, g

SQLITE = "sqlite"
POSTGRES = "postgres"

#: Set once the schema has been created, so it is attempted only until it works.
SCHEMA_READY = "db_schema_ready"


class DatabaseUnavailable(RuntimeError):
    """The database could not be reached or prepared."""

POSTGRES_SCHEMES = ("postgres://", "postgresql://")


def _serial(dialect: str) -> str:
    return "BIGSERIAL PRIMARY KEY" if dialect == POSTGRES else "INTEGER PRIMARY KEY AUTOINCREMENT"


def schema_statements(dialect: str) -> list[str]:
    """DDL for the whole schema.

    Emails are lower-cased before they are stored or looked up, so a plain
    UNIQUE constraint gives case-insensitive accounts on both engines.

    ``question_bundles`` holds the question bank for deployments that cannot
    ship it in the repository; one row per test, so serving a module does not
    read the whole bank.
    """
    return [
        f"""
        CREATE TABLE IF NOT EXISTS users (
            id            {_serial(dialect)},
            email         TEXT    NOT NULL UNIQUE,
            username      TEXT    NOT NULL,
            password_hash TEXT    NOT NULL,
            created_at    TEXT    NOT NULL,
            last_login_at TEXT,
            is_disabled   INTEGER NOT NULL DEFAULT 0
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS sessions (
            token_hash TEXT PRIMARY KEY,
            user_id    BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            created_at TEXT NOT NULL,
            expires_at TEXT NOT NULL
        )
        """,
        "CREATE INDEX IF NOT EXISTS idx_sessions_user ON sessions(user_id)",
        f"""
        CREATE TABLE IF NOT EXISTS attempts (
            id       {_serial(dialect)},
            user_id  BIGINT  NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            taken_at TEXT    NOT NULL,
            score    INTEGER NOT NULL,
            correct  INTEGER NOT NULL,
            total    INTEGER NOT NULL,
            details  TEXT    NOT NULL
        )
        """,
        "CREATE INDEX IF NOT EXISTS idx_attempts_user ON attempts(user_id, taken_at DESC)",
        """
        CREATE TABLE IF NOT EXISTS question_bundles (
            test_id    TEXT    PRIMARY KEY,
            position   INTEGER NOT NULL,
            payload    TEXT    NOT NULL,
            updated_at TEXT    NOT NULL
        )
        """,
        "CREATE INDEX IF NOT EXISTS idx_bundles_position ON question_bundles(position)",
    ]


class Database:
    """One SQL dialect over sqlite3 or psycopg."""

    def __init__(self, connection: Any, dialect: str) -> None:
        self._connection = connection
        self.dialect = dialect

    @property
    def is_postgres(self) -> bool:
        return self.dialect == POSTGRES

    def _sql(self, sql: str) -> str:
        # psycopg uses %s; sqlite3 uses ?. No statement here contains a literal
        # '?' or '%', so a straight swap is safe.
        return sql.replace("?", "%s") if self.is_postgres else sql

    def execute(self, sql: str, params: Sequence[Any] = ()) -> Any:
        cursor = self._connection.cursor()
        cursor.execute(self._sql(sql), tuple(params))
        return cursor

    def fetch_one(self, sql: str, params: Sequence[Any] = ()) -> Mapping[str, Any] | None:
        return self.execute(sql, params).fetchone()

    def fetch_all(self, sql: str, params: Sequence[Any] = ()) -> list[Mapping[str, Any]]:
        return list(self.execute(sql, params).fetchall())

    def insert(self, sql: str, params: Sequence[Any] = ()) -> int:
        """Run an INSERT and return the new row's id."""
        if self.is_postgres:
            row = self.execute(f"{sql.rstrip().rstrip(';')} RETURNING id", params).fetchone()
            return int(row["id"])
        return int(self.execute(sql, params).lastrowid)

    def commit(self) -> None:
        self._connection.commit()

    def rollback(self) -> None:
        self._connection.rollback()

    def close(self) -> None:
        self._connection.close()

    def init_schema(self) -> None:
        for statement in schema_statements(self.dialect):
            self.execute(statement)
        self.commit()


def _connect_sqlite(path: str | Path) -> Database:
    path = Path(path)
    if str(path) != ":memory:":
        path.parent.mkdir(parents=True, exist_ok=True)

    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    # Foreign keys are off by default in SQLite; deletes have to cascade.
    connection.execute("PRAGMA foreign_keys = ON")
    connection.execute("PRAGMA journal_mode = WAL")
    return Database(connection, SQLITE)


def _connect_postgres(url: str) -> Database:
    try:
        import psycopg
        from psycopg.rows import dict_row
    except ImportError as error:  # pragma: no cover - depends on the install
        raise RuntimeError(
            "DATABASE_URL points at PostgreSQL but psycopg is not installed; "
            "add 'psycopg[binary]' to your requirements"
        ) from error

    return Database(psycopg.connect(url, row_factory=dict_row, autocommit=False), POSTGRES)


def connect(target: str | Path) -> Database:
    """Open a connection to a PostgreSQL URL or a SQLite file path."""
    text = str(target)
    if text.startswith(POSTGRES_SCHEMES):
        return _connect_postgres(text)
    return _connect_sqlite(target)


def database_target(config: Mapping[str, Any]) -> str:
    """A connection URL if one is configured, else the SQLite file path."""
    return str(config.get("DATABASE_URL") or config["DATABASE_PATH"])


def get_db() -> Database:
    """The connection for the current request, opened on first use.

    If the schema could not be created at startup — a serverless host with no
    database configured yet, for instance — this retries it here so the app
    recovers as soon as the database becomes reachable.
    """
    from flask import current_app

    if "db" in g:
        return g.db

    try:
        database = connect(database_target(current_app.config))
        if not current_app.extensions.get(SCHEMA_READY):
            database.init_schema()
            current_app.extensions[SCHEMA_READY] = True
    except Exception as error:
        raise DatabaseUnavailable(str(error)) from error

    g.db = database
    return g.db


def close_db(_exception: BaseException | None = None) -> None:
    database = g.pop("db", None)
    if database is not None:
        database.close()


def init_app(app: Flask) -> None:
    """Create the schema once at startup and close connections per request.

    Startup must not fail when the database is unreachable: on a serverless host
    the disk is read-only, so an unconfigured database would otherwise crash the
    whole application at import time and take the question bank down with it.
    The schema is retried on the first request that needs it.
    """
    app.teardown_appcontext(close_db)
    app.extensions[SCHEMA_READY] = False

    try:
        database = connect(database_target(app.config))
        try:
            database.init_schema()
            app.extensions[SCHEMA_READY] = True
        finally:
            database.close()
    except Exception as error:
        app.logger.warning(
            "Database not ready at startup (%s); accounts stay unavailable until "
            "DATABASE_URL points at a reachable database.",
            error,
        )
