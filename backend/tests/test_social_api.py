"""Friend requests and messages."""


def register(client, name, email):
    response = client.post(
        "/api/auth/register", json={"email": email, "username": name, "password": "sup3rsecret"}
    )
    assert response.status_code == 201
    return {"Authorization": f"Bearer {response.get_json()['token']}"}, response.get_json()["user"]


def test_a_request_becomes_a_friendship_when_accepted(client, auth_headers, registered):
    other_headers, other = register(client, "Farrukh", "farrukh@example.com")

    sent = client.post("/api/friends/requests", json={"user_id": other["id"]}, headers=auth_headers)
    assert sent.status_code == 201
    assert sent.get_json()["relationship"] == "outgoing"

    mine = client.get("/api/friends", headers=auth_headers).get_json()
    assert [f["user"]["username"] for f in mine["outgoing"]] == ["Farrukh"]
    theirs = client.get("/api/friends", headers=other_headers).get_json()
    assert [f["user"]["username"] for f in theirs["incoming"]] == ["Nika"]
    request_id = theirs["incoming"][0]["request_id"]

    # Only the addressee can accept.
    assert client.post(f"/api/friends/requests/{request_id}/accept", headers=auth_headers).status_code == 409
    accepted = client.post(f"/api/friends/requests/{request_id}/accept", headers=other_headers)
    assert accepted.status_code == 200

    for headers, name in ((auth_headers, "Farrukh"), (other_headers, "Nika")):
        overview = client.get("/api/friends", headers=headers).get_json()
        assert [f["user"]["username"] for f in overview["friends"]] == [name]
        assert overview["friends"][0]["user"]["tier"] == "basic", "the list carries the tier it shows"
        assert overview["incoming"] == [] and overview["outgoing"] == []

    profile = client.get(f"/api/users/{other['id']}", headers=auth_headers).get_json()
    assert profile["relationship"] == "friends"
    assert profile["friends_count"] == 1

    assert client.delete(f"/api/friends/{other['id']}", headers=auth_headers).status_code == 204
    assert client.get("/api/friends", headers=auth_headers).get_json()["friends"] == []


def test_asking_back_accepts_and_the_rest_is_refused(client, auth_headers, registered):
    other_headers, other = register(client, "Farrukh", "farrukh@example.com")
    client.post("/api/friends/requests", json={"user_id": registered["user"]["id"]}, headers=other_headers)

    answered = client.post("/api/friends/requests", json={"user_id": other["id"]}, headers=auth_headers)
    assert answered.status_code == 201
    assert answered.get_json()["relationship"] == "friends"

    assert client.post("/api/friends/requests", json={"user_id": other["id"]}, headers=auth_headers).status_code == 409
    me = registered["user"]["id"]
    assert client.post("/api/friends/requests", json={"user_id": me}, headers=auth_headers).status_code == 409
    assert client.post("/api/friends/requests", json={"user_id": 9999}, headers=auth_headers).status_code == 404
    assert client.post("/api/friends/requests", json={}, headers=auth_headers).status_code == 422


def test_a_request_can_be_declined_or_taken_back(client, auth_headers):
    other_headers, other = register(client, "Farrukh", "farrukh@example.com")
    client.post("/api/friends/requests", json={"user_id": other["id"]}, headers=auth_headers)
    request_id = client.get("/api/friends", headers=other_headers).get_json()["incoming"][0]["request_id"]

    assert client.delete(f"/api/friends/requests/{request_id}", headers=other_headers).status_code == 204
    assert client.get("/api/friends", headers=auth_headers).get_json()["outgoing"] == []


def test_messages_travel_and_are_read_when_the_thread_is_opened(client, auth_headers, registered):
    other_headers, other = register(client, "Farrukh", "farrukh@example.com")
    me = registered["user"]["id"]

    sent = client.post(f"/api/messages/{other['id']}", json={"body": "  Hi! Want to practise?  "}, headers=auth_headers)
    assert sent.status_code == 201
    assert sent.get_json()["message"]["body"] == "Hi! Want to practise?"

    inbox = client.get("/api/messages", headers=other_headers).get_json()
    assert inbox["unread"] == 1
    assert inbox["conversations"][0]["user"]["username"] == "Nika"
    assert inbox["conversations"][0]["user"]["tier"] == "basic"
    assert inbox["conversations"][0]["unread"] == 1
    assert inbox["conversations"][0]["last_message"]["mine"] is False

    thread = client.get(f"/api/messages/{me}", headers=other_headers).get_json()
    assert [m["body"] for m in thread["messages"]] == ["Hi! Want to practise?"]
    assert client.get("/api/messages", headers=other_headers).get_json()["unread"] == 0

    client.post(f"/api/messages/{me}", json={"body": "Sure"}, headers=other_headers)
    thread = client.get(f"/api/messages/{other['id']}", headers=auth_headers).get_json()
    assert [m["body"] for m in thread["messages"]] == ["Hi! Want to practise?", "Sure"]
    assert [m["sender_id"] == me for m in thread["messages"]] == [True, False]

    assert client.post(f"/api/messages/{other['id']}", json={"body": "   "}, headers=auth_headers).status_code == 422
    assert client.post(f"/api/messages/{me}", json={"body": "self"}, headers=auth_headers).status_code == 409
    assert client.post("/api/messages/9999", json={"body": "?"}, headers=auth_headers).status_code == 404
    assert client.get("/api/messages").status_code == 401


def test_a_friend_request_notifies_and_its_answer_notifies_back(client, auth_headers, registered):
    other_headers, other = register(client, "Farrukh", "farrukh@example.com")
    assert client.get("/api/notifications", headers=other_headers).get_json() == {"notifications": [], "unread": 0}

    client.post("/api/friends/requests", json={"user_id": other["id"]}, headers=auth_headers)
    inbox = client.get("/api/notifications", headers=other_headers).get_json()
    assert inbox["unread"] == 1
    [note] = inbox["notifications"]
    assert note["kind"] == "friend_request" and note["pending"] is True and note["read"] is False
    assert note["user"]["username"] == "Nika"
    assert "email" not in note["user"], "only the public profile travels"

    request_id = note["ref_id"]
    client.post(f"/api/friends/requests/{request_id}/accept", headers=other_headers)
    inbox = client.get("/api/notifications", headers=other_headers).get_json()
    assert inbox["unread"] == 0, "answering the request reads its notification"
    assert inbox["notifications"][0]["pending"] is False

    mine = client.get("/api/notifications", headers=auth_headers).get_json()
    assert mine["unread"] == 1
    assert mine["notifications"][0]["kind"] == "friend_accepted"
    assert mine["notifications"][0]["user"]["username"] == "Farrukh"


def test_a_request_taken_back_takes_its_notification_with_it(client, auth_headers):
    other_headers, other = register(client, "Farrukh", "farrukh@example.com")
    client.post("/api/friends/requests", json={"user_id": other["id"]}, headers=auth_headers)
    request_id = client.get("/api/friends", headers=auth_headers).get_json()["outgoing"][0]["request_id"]

    client.delete(f"/api/friends/requests/{request_id}", headers=auth_headers)
    assert client.get("/api/notifications", headers=other_headers).get_json() == {"notifications": [], "unread": 0}


def test_notifications_are_marked_read_one_or_all(client, auth_headers):
    other_headers, other = register(client, "Farrukh", "farrukh@example.com")
    third_headers, third = register(client, "Dilnoza", "dilnoza@example.com")
    client.post("/api/friends/requests", json={"user_id": third["id"]}, headers=auth_headers)
    client.post("/api/friends/requests", json={"user_id": third["id"]}, headers=other_headers)

    notes = client.get("/api/notifications", headers=third_headers).get_json()["notifications"]
    one = client.post("/api/notifications/read", json={"id": notes[0]["id"]}, headers=third_headers)
    assert one.get_json() == {"unread": 1}
    # Someone else's notification is not theirs to read.
    assert client.post("/api/notifications/read", json={"id": notes[1]["id"]}, headers=other_headers).get_json() == {"unread": 0}
    assert client.get("/api/notifications", headers=third_headers).get_json()["unread"] == 1

    assert client.post("/api/notifications/read", headers=third_headers).get_json() == {"unread": 0}
    assert client.post("/api/notifications/read", json={"id": "x"}, headers=third_headers).status_code == 422
    assert client.get("/api/notifications").status_code == 401
