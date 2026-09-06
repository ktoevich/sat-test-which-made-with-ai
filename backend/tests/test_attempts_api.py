def post_attempt(client, headers, **overrides):
    payload = {"score": 680, "correct": 4, "total": 5, "details": [{"number": 1}]}
    payload.update(overrides)
    return client.post("/api/attempts", json=payload, headers=headers)


def test_attempts_require_a_session(client):
    assert client.get("/api/attempts").status_code == 401
    assert client.post("/api/attempts", json={"score": 1, "correct": 1, "total": 1}).status_code == 401


def test_a_new_account_has_no_attempts(client, auth_headers):
    payload = client.get("/api/attempts", headers=auth_headers).get_json()
    assert payload["attempts"] == []
    assert payload["summary"] == {"taken": 0, "best": None, "average": None}


def test_recording_an_attempt_shows_up_in_the_history(client, auth_headers):
    assert post_attempt(client, auth_headers).status_code == 201

    payload = client.get("/api/attempts", headers=auth_headers).get_json()
    assert len(payload["attempts"]) == 1

    attempt = payload["attempts"][0]
    assert attempt["score"] == 680
    assert attempt["correct"] == 4
    assert attempt["details"] == [{"number": 1}]
    assert attempt["taken_at"]


def test_the_summary_aggregates_every_attempt(client, auth_headers):
    for score in (500, 700, 600):
        post_attempt(client, auth_headers, score=score)

    summary = client.get("/api/attempts", headers=auth_headers).get_json()["summary"]
    assert summary == {"taken": 3, "best": 700, "average": 600}


def test_attempts_are_returned_newest_first(client, auth_headers):
    for score in (400, 500, 600):
        post_attempt(client, auth_headers, score=score)

    scores = [a["score"] for a in client.get("/api/attempts", headers=auth_headers).get_json()["attempts"]]
    assert scores == [600, 500, 400]


def test_invalid_payloads_are_rejected(client, auth_headers):
    for overrides in ({"score": None}, {"total": 0}, {"correct": 9, "total": 5}, {"correct": -1}):
        response = post_attempt(client, auth_headers, **overrides)
        assert response.status_code == 422, overrides


def test_one_user_cannot_see_another_users_history(client, auth_headers):
    post_attempt(client, auth_headers)

    other = client.post(
        "/api/auth/register",
        json={"email": "other@example.com", "username": "Other", "password": "sup3rsecret"},
    ).get_json()
    other_headers = {"Authorization": f"Bearer {other['token']}"}

    assert client.get("/api/attempts", headers=other_headers).get_json()["attempts"] == []


def test_deleting_a_user_removes_their_attempts(client, db, registered, auth_headers):
    from app.services import accounts, attempts

    post_attempt(client, auth_headers)
    user_id = registered["user"]["id"]
    assert attempts.list_for_user(db, user_id)

    accounts.delete_user(db, user_id)
    assert attempts.list_for_user(db, user_id) == []
