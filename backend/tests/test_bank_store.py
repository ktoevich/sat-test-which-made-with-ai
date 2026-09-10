"""The question bank served out of the database instead of the bank file.

A deployment that cannot commit its bank pushes it into the database; these
tests pin the three states that follow from that — database wins, empty
database falls back to the file, and no database at all still serves.
"""

import json

import pytest

from app import create_app
from app.services import bank_store
from tests.conftest import make_question


def other_bundle(test_id: str = "from-database") -> dict:
    return {
        "test_id": test_id,
        "module_1": [make_question(f"{test_id}-1", "MCQ", "Easy")],
        "module_2_HIGHER": [make_question(f"{test_id}-2", "MCQ", "Hard")],
        "module_2_LOWER": [make_question(f"{test_id}-3", "MCQ", "Easy")],
    }


def test_a_pushed_bank_replaces_what_was_there(db):
    db.init_schema()
    assert bank_store.count(db) == 0

    bank_store.replace_all(db, [other_bundle("first"), other_bundle("second")])
    assert bank_store.count(db) == 2
    assert bank_store.test_ids(db) == ["first", "second"]

    # A bundle dropped from the bank must not linger and get served.
    bank_store.replace_all(db, [other_bundle("second")])
    assert bank_store.test_ids(db) == ["second"]


def test_bundles_come_back_exactly_as_they_went_in(db):
    db.init_schema()
    bundle = other_bundle()
    bank_store.replace_all(db, [bundle])
    assert bank_store.fetch(db, "from-database") == bundle
    assert bank_store.fetch(db, "no-such-test") is None
    assert bank_store.fetch_all(db) == [bundle]


def test_a_random_draw_only_returns_a_stored_test(db):
    db.init_schema()
    bank_store.replace_all(db, [other_bundle("a"), other_bundle("b")])
    for _ in range(20):
        assert bank_store.fetch_random(db)["test_id"] in {"a", "b"}


def test_clearing_hands_the_bank_back_to_the_file(db):
    db.init_schema()
    bank_store.replace_all(db, [other_bundle()])
    assert bank_store.clear(db) == 1
    assert bank_store.count(db) == 0
    assert bank_store.fetch_random(db) is None


def test_the_api_serves_the_stored_bank_over_the_file(client, db):
    """The file holds bundle-1; the database holds another. The database wins."""
    db.init_schema()
    bank_store.replace_all(db, [other_bundle()])

    assert client.get("/api/health").get_json()["tests_available"] == 1

    body = client.get("/api/tests/module-1").get_json()
    assert body["test_id"] == "from-database"

    second = client.get("/api/tests/module-2?test_id=from-database&target=HIGHER")
    assert second.status_code == 200
    assert second.get_json()["test_id"] == "from-database"


def test_the_file_still_answers_when_the_database_holds_no_bank(client):
    assert client.get("/api/health").get_json()["tests_available"] == 1
    assert client.get("/api/tests/module-1").get_json()["test_id"] == "bundle-1"


def test_the_bank_survives_a_database_that_cannot_be_reached(bank_path, tmp_path):
    """The bank must never be taken down by an unconfigured database.

    A serverless host starts with no database attached; the student should
    still get a test.
    """
    app = create_app(
        "testing",
        QUESTION_BANK_PATH=bank_path,
        DATABASE_URL="postgres://nobody@127.0.0.1:1/nothing",
    )
    client = app.test_client()
    assert client.get("/api/health").get_json()["tests_available"] == 1
    assert client.get("/api/tests/module-1").status_code == 200


def test_an_empty_bank_is_still_reported_as_empty(tmp_path):
    app = create_app(
        "testing",
        QUESTION_BANK_PATH=tmp_path / "missing.json",
        DATABASE_PATH=tmp_path / "empty.db",
    )
    client = app.test_client()
    assert client.get("/api/health").get_json()["tests_available"] == 0
    assert client.get("/api/tests/module-1").status_code == 503
