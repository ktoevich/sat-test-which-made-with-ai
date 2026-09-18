def test_health_reports_available_tests_per_section(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.get_json() == {
        "status": "ok",
        "tests_available": 2,
        "sections": {"math": 1, "reading": 1},
    }


def test_module_1_returns_ordered_questions(client):
    response = client.get("/api/tests/module-1")
    assert response.status_code == 200

    payload = response.get_json()
    assert payload["test_id"] == "bundle-1"
    assert payload["section"] == "math"
    assert payload["module"] == 1
    assert [q["id"] for q in payload["questions"]] == [1, 2, 3]
    # Easy -> Medium -> Hard, grid-ins wherever their difficulty puts them.
    assert [q["question_id"] for q in payload["questions"]] == ["m1-easy", "m1-spr", "m1-hard"]


def test_a_reading_module_is_grouped_by_domain_then_difficulty(client):
    response = client.get("/api/tests/module-1?section=reading")
    assert response.status_code == 200

    payload = response.get_json()
    assert payload["test_id"] == "reading-1"
    assert payload["section"] == "reading"
    # Craft and Structure before Standard English Conventions; easy first inside.
    assert [q["question_id"] for q in payload["questions"]] == [
        "r1-craft-easy",
        "r1-craft-hard",
        "r1-conventions",
    ]
    assert payload["questions"][0]["passage"] == "<p>Passage r1-craft-easy</p>"

    second = client.get("/api/tests/module-2?test_id=reading-1&target=LOWER")
    assert second.get_json()["section"] == "reading"
    assert second.get_json()["questions"][0]["question_id"] == "r2l"


def test_an_unknown_section_is_rejected(client):
    response = client.get("/api/tests/module-1?section=science")
    assert response.status_code == 422
    assert response.get_json()["error"]["code"] == "validation_failed"


def test_a_section_with_no_tests_is_reported_empty(tmp_path, bundle):
    import json

    from app import create_app

    path = tmp_path / "math-only.json"
    path.write_text(json.dumps([bundle]), encoding="utf-8")
    client = create_app(
        "testing", QUESTION_BANK_PATH=path, DATABASE_PATH=tmp_path / "math-only.db"
    ).test_client()

    assert client.get("/api/tests/module-1").status_code == 200
    response = client.get("/api/tests/module-1?section=reading")
    assert response.status_code == 503
    assert response.get_json()["error"]["code"] == "bank_empty"
    assert client.get("/api/health").get_json()["sections"] == {"math": 1, "reading": 0}


def test_module_2_follows_the_requested_target(client):
    response = client.get("/api/tests/module-2?test_id=bundle-1&target=LOWER")
    assert response.status_code == 200
    assert response.get_json()["questions"][0]["question_id"] == "m2l"


def test_module_2_rejects_unknown_test_id(client):
    response = client.get("/api/tests/module-2?test_id=nope&target=HIGHER")
    assert response.status_code == 404
    assert response.get_json()["error"]["code"] == "test_not_found"


def test_module_2_rejects_unknown_target(client):
    response = client.get("/api/tests/module-2?test_id=bundle-1&target=SIDEWAYS")
    assert response.status_code == 422
    assert response.get_json()["error"]["code"] == "validation_failed"


def test_empty_bank_returns_service_unavailable(empty_client):
    response = empty_client.get("/api/tests/module-1")
    assert response.status_code == 503
    assert response.get_json()["error"]["code"] == "bank_empty"


def test_unknown_api_path_returns_json(client):
    response = client.get("/api/nope")
    assert response.status_code == 404
    assert response.get_json()["error"]["code"] == "not_found"


def test_an_unexpected_error_is_answered_with_the_envelope(app, client, monkeypatch):
    """A bug must never be answered with a stack trace.

    Werkzeug's 500 page carries file paths, source lines and whatever a driver
    put in its message — for a failed connection, that can include the
    database URL.
    """
    bank = app.extensions["question_bank"]
    monkeypatch.setattr(
        type(bank), "random_bundle", lambda self, **kw: 1 / 0, raising=True
    )

    response = client.get("/api/tests/module-1")
    assert response.status_code == 500

    body = response.get_json()
    assert body["error"]["code"] == "internal_error"
    assert "ZeroDivisionError" not in response.get_data(as_text=True)
    assert "Traceback" not in response.get_data(as_text=True)


def test_a_missing_endpoint_still_reads_as_not_found(client):
    """The catch-all must not swallow the ordinary HTTP errors."""
    response = client.get("/api/nope")
    assert response.status_code == 404
    assert response.get_json()["error"]["code"] == "not_found"
