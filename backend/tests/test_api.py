def test_health_reports_available_tests(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.get_json() == {"status": "ok", "tests_available": 1}


def test_module_1_returns_ordered_questions(client):
    response = client.get("/api/tests/module-1")
    assert response.status_code == 200

    payload = response.get_json()
    assert payload["test_id"] == "bundle-1"
    assert payload["module"] == 1
    assert [q["id"] for q in payload["questions"]] == [1, 2, 3]
    # Easy -> Medium -> Hard, grid-ins wherever their difficulty puts them.
    assert [q["question_id"] for q in payload["questions"]] == ["m1-easy", "m1-spr", "m1-hard"]


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
    assert response.get_json()["error"]["code"] == "invalid_request"


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
