def test_register_returns_a_token_and_the_user(client):
    response = client.post(
        "/api/auth/register",
        json={"email": "New@Example.com", "username": "Nika", "password": "sup3rsecret"},
    )
    assert response.status_code == 201

    payload = response.get_json()
    assert payload["token"]
    assert payload["user"]["email"] == "new@example.com", "email should be normalised"
    assert payload["user"]["username"] == "Nika"
    assert "password" not in str(payload)


def test_register_rejects_a_duplicate_email(client, registered):
    response = client.post(
        "/api/auth/register",
        json={"email": "student@example.com", "username": "Other", "password": "sup3rsecret"},
    )
    assert response.status_code == 409
    assert response.get_json()["error"]["code"] == "email_taken"


def test_register_validates_its_input(client):
    cases = [
        {"email": "not-an-email", "username": "N", "password": "sup3rsecret"},
        {"email": "a@b.com", "username": "", "password": "sup3rsecret"},
        {"email": "a@b.com", "username": "N", "password": "short"},
    ]
    for payload in cases:
        response = client.post("/api/auth/register", json=payload)
        assert response.status_code == 422, payload
        assert response.get_json()["error"]["code"] == "validation_failed"


def test_login_succeeds_regardless_of_email_case(client, registered):
    response = client.post(
        "/api/auth/login", json={"email": "STUDENT@example.com", "password": "sup3rsecret"}
    )
    assert response.status_code == 200
    assert response.get_json()["user"]["username"] == "Nika"


def test_login_rejects_a_wrong_password(client, registered):
    response = client.post(
        "/api/auth/login", json={"email": "student@example.com", "password": "nope"}
    )
    assert response.status_code == 401
    assert response.get_json()["error"]["code"] == "invalid_credentials"


def test_an_unknown_email_gives_the_same_error_as_a_wrong_password(client):
    response = client.post(
        "/api/auth/login", json={"email": "ghost@example.com", "password": "whatever"}
    )
    assert response.status_code == 401
    assert response.get_json()["error"]["code"] == "invalid_credentials"


def test_login_records_the_time(client, registered):
    assert registered["user"]["last_login_at"] is None
    client.post("/api/auth/login", json={"email": "student@example.com", "password": "sup3rsecret"})

    me = client.get("/api/auth/me", headers={"Authorization": f"Bearer {registered['token']}"})
    assert me.get_json()["user"]["last_login_at"] is not None


def test_me_needs_a_valid_token(client):
    assert client.get("/api/auth/me").status_code == 401
    assert client.get("/api/auth/me", headers={"Authorization": "Bearer nope"}).status_code == 401


def test_logout_invalidates_the_token(client, registered, auth_headers):
    assert client.post("/api/auth/logout", headers=auth_headers).status_code == 204
    assert client.get("/api/auth/me", headers=auth_headers).status_code == 401


def test_a_disabled_account_cannot_use_its_token(client, db, registered, auth_headers):
    from app.services import accounts

    accounts.set_disabled(db, registered["user"]["id"], True)
    assert client.get("/api/auth/me", headers=auth_headers).status_code == 401

    response = client.post(
        "/api/auth/login", json={"email": "student@example.com", "password": "sup3rsecret"}
    )
    assert response.status_code == 403
    assert response.get_json()["error"]["code"] == "account_disabled"


def test_resetting_a_password_ends_existing_sessions(client, db, registered, auth_headers):
    from app.services import accounts

    accounts.set_password(db, registered["user"]["id"], "brandnewpass", iterations=1_000)
    assert client.get("/api/auth/me", headers=auth_headers).status_code == 401

    response = client.post(
        "/api/auth/login", json={"email": "student@example.com", "password": "brandnewpass"}
    )
    assert response.status_code == 200
