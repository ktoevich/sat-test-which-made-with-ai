import json
import os
from pathlib import Path

import pytest

from app import create_app
from app.db import connect

#: Set this to a postgres:// URL to run the suite against PostgreSQL instead of
#: SQLite, which is what the deployed app uses:
#:   TEST_DATABASE_URL=postgres://... pytest
TEST_DATABASE_URL = os.environ.get("TEST_DATABASE_URL", "")


def make_question(question_id: str, qtype: str, difficulty: str) -> dict:
    return {
        "question_id": question_id,
        "type": qtype,
        "difficulty": difficulty,
        "text": f"Question {question_id}",
        "options": ["A) 1", "B) 2", "C) 3", "D) 4"] if qtype == "MCQ" else None,
        "answer": "A" if qtype == "MCQ" else "12",
    }


@pytest.fixture
def bundle() -> dict:
    return {
        "test_id": "bundle-1",
        "module_1": [
            make_question("m1-hard", "MCQ", "Hard"),
            make_question("m1-easy", "MCQ", "Easy"),
            make_question("m1-spr", "SPR", "Medium"),
        ],
        "module_2_HIGHER": [make_question("m2h", "MCQ", "Hard")],
        "module_2_LOWER": [make_question("m2l", "MCQ", "Easy")],
    }


@pytest.fixture
def bank_path(tmp_path: Path, bundle: dict) -> Path:
    path = tmp_path / "bank.json"
    path.write_text(json.dumps([bundle]), encoding="utf-8")
    return path


def _reset(url: str) -> None:
    """Drop every table so each test starts from an empty database."""
    database = connect(url)
    try:
        database.execute("DROP TABLE IF EXISTS attempts, sessions, users CASCADE")
        database.commit()
    finally:
        database.close()


@pytest.fixture
def app(bank_path: Path, tmp_path: Path):
    overrides = {"QUESTION_BANK_PATH": bank_path}
    if TEST_DATABASE_URL:
        _reset(TEST_DATABASE_URL)
        overrides["DATABASE_URL"] = TEST_DATABASE_URL
    else:
        overrides["DATABASE_PATH"] = tmp_path / "test.db"
    return create_app("testing", **overrides)


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def empty_client(tmp_path: Path):
    app = create_app(
        "testing",
        QUESTION_BANK_PATH=tmp_path / "missing.json",
        DATABASE_PATH=tmp_path / "empty.db",
    )
    return app.test_client()


@pytest.fixture
def db(app):
    """A connection to the same database the test client uses."""
    from app.db import connect, database_target

    database = connect(database_target(app.config))
    yield database
    database.close()


@pytest.fixture
def registered(client):
    """A signed-up user plus their session token."""
    response = client.post(
        "/api/auth/register",
        json={"email": "Student@Example.com", "username": "Nika", "password": "sup3rsecret"},
    )
    assert response.status_code == 201, response.get_json()
    return response.get_json()


@pytest.fixture
def auth_headers(registered):
    return {"Authorization": f"Bearer {registered['token']}"}
