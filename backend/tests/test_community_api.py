"""Profiles, ratings, the leaderboard and the platform's numbers."""

from app.db import connect
from app.services import ratings


def register(client, name, email="x@example.com"):
    response = client.post(
        "/api/auth/register", json={"email": email, "username": name, "password": "sup3rsecret"}
    )
    assert response.status_code == 201, response.get_json()
    return {"Authorization": f"Bearer {response.get_json()['token']}"}, response.get_json()["user"]


def attempt(client, headers, **overrides):
    payload = {"score": 700, "correct": 4, "total": 5, "details": [], "section": "math", "time_spent": 1800}
    payload.update(overrides)
    response = client.post("/api/attempts", json=payload, headers=headers)
    assert response.status_code == 201, response.get_json()
    return response.get_json()["attempt"]


def test_a_new_account_starts_basic_with_the_starting_rating(registered):
    user = registered["user"]
    assert user["rating"] == ratings.START_RATING
    assert user["max_rating"] == ratings.START_RATING
    assert user["top_score"] is None
    assert user["tier"] == "basic"
    assert user["avatar"] == "" and user["full_name"] == "" and user["location"] == ""


def test_the_profile_can_be_edited_field_by_field(client, auth_headers):
    response = client.patch(
        "/api/auth/profile",
        json={"avatar": "🦉", "full_name": "  Nika   Ivanova ", "location": "Tajikistan, Dushanbe"},
        headers=auth_headers,
    )
    assert response.status_code == 200
    user = response.get_json()["user"]
    assert (user["avatar"], user["full_name"], user["location"]) == ("🦉", "Nika Ivanova", "Tajikistan, Dushanbe")
    assert user["username"] == "Nika", "a field left out is kept"

    me = client.get("/api/auth/me", headers=auth_headers).get_json()["user"]
    assert me["avatar"] == "🦉"


def test_the_profile_rejects_what_it_should(client, auth_headers):
    for payload in (
        {"username": ""},
        {"avatar": "https://evil.example/x.png"},
        {"avatar": "<img>"},
        {"full_name": "x" * 81},
        {},
    ):
        response = client.patch("/api/auth/profile", json=payload, headers=auth_headers)
        assert response.status_code == 422, payload


def test_every_attempt_moves_the_rating_and_records_the_move(client, auth_headers):
    first = attempt(client, auth_headers, score=800, test_id="sat-imported-03", target="HIGHER")
    assert first["rating_before"] == 1200
    assert first["rating_after"] == 1290
    assert first["test_id"] == "sat-imported-03"
    assert first["target"] == "HIGHER"
    assert first["time_spent"] == 1800

    second = attempt(client, auth_headers, score=400)
    assert (second["rating_before"], second["rating_after"]) == (1290, 1200)

    me = client.get("/api/auth/me", headers=auth_headers).get_json()["user"]
    assert me["rating"] == 1200
    assert me["max_rating"] == 1290, "the peak stays"


def test_the_rating_never_falls_through_the_floor():
    rating = ratings.START_RATING
    for _ in range(20):
        rating = ratings.apply(rating, 200)
    assert rating == ratings.FLOOR


def test_the_tier_is_the_band_of_the_best_score():
    assert ratings.tier(None) == "basic"
    assert [ratings.tier(s) for s in (200, 499, 500, 599, 600, 699, 700, 800)] == [
        "basic", "basic", "intermediate", "intermediate", "advanced", "advanced", "elite", "elite",
    ]


def test_the_best_score_in_any_section_sets_the_tier_and_a_worse_one_keeps_it(client, auth_headers):
    attempt(client, auth_headers, score=560, section="math")
    me = client.get("/api/auth/me", headers=auth_headers).get_json()["user"]
    assert (me["top_score"], me["tier"]) == (560, "intermediate")

    attempt(client, auth_headers, score=710, section="reading")
    attempt(client, auth_headers, score=300, section="math")
    me = client.get("/api/auth/me", headers=auth_headers).get_json()["user"]
    assert (me["top_score"], me["tier"]) == (710, "elite"), "a bad day does not take the tier away"


def test_a_database_from_before_the_tiers_gets_its_best_scores_filled_in():
    db = connect(":memory:")
    db.init_schema()
    user_id = db.insert(
        "INSERT INTO users (email, username, password_hash, created_at) VALUES (?, ?, ?, ?)",
        ("old@example.com", "Old", "x", "2026-01-01T00:00:00+00:00"),
    )
    for score in (540, 690):
        db.execute(
            "INSERT INTO attempts (user_id, taken_at, score, correct, total, details) VALUES (?, ?, ?, ?, ?, ?)",
            (user_id, "2026-01-02T00:00:00+00:00", score, 1, 2, "[]"),
        )
    db.commit()
    assert db.fetch_one("SELECT top_score FROM users WHERE id = ?", (user_id,))["top_score"] is None

    db.init_schema()  # the next start of the app
    assert db.fetch_one("SELECT top_score FROM users WHERE id = ?", (user_id,))["top_score"] == 690
    db.close()


def test_students_can_be_searched_by_handle_or_name(client, auth_headers):
    other_headers, other = register(client, "Farrukh", "farrukh@example.com")
    client.patch("/api/auth/profile", json={"full_name": "Farrukh Nazarov"}, headers=other_headers)

    found = client.get("/api/users/search?q=nazar", headers=auth_headers).get_json()["users"]
    assert [u["username"] for u in found] == ["Farrukh"]
    assert "email" not in found[0], "a public entry never carries the email"

    everyone = client.get("/api/users/search?q=", headers=auth_headers).get_json()["users"]
    assert {u["username"] for u in everyone} == {"Nika", "Farrukh"}
    assert client.get("/api/users/search?q=x").status_code == 401


def test_a_public_profile_shows_history_without_breakdowns_and_real_topic_counts(client, auth_headers):
    other_headers, other = register(client, "Farrukh", "farrukh@example.com")
    details = [
        {"module": 1, "number": 1, "question": {"domain": "Algebra", "type": "MCQ", "answer": "A"}, "userAnswer": "A"},
        {"module": 1, "number": 2, "question": {"domain": "Algebra", "type": "MCQ", "answer": "B"}, "userAnswer": "C"},
        {"module": 1, "number": 3, "question": {"domain": "Geometry and Trigonometry", "type": "SPR", "answer": "0.5"}, "userAnswer": "1/2"},
    ]
    attempt(client, other_headers, score=650, details=details)

    response = client.get(f"/api/users/{other['id']}", headers=auth_headers)
    assert response.status_code == 200
    profile = response.get_json()
    assert profile["user"]["username"] == "Farrukh"
    assert "email" not in profile["user"]
    assert profile["summary"]["by_section"]["math"]["best"] == 650
    assert profile["user"]["tier"] == "advanced"
    assert "details" not in profile["history"][0]
    assert profile["history"][0]["score"] == 650
    assert profile["relationship"] == "none"
    assert profile["friends_count"] == 0

    points = profile["analytics"]["rating_points"]
    assert [(p["rating_before"], p["rating_after"]) for p in points] == [(1200, 1222)]
    topics = {(t["section"], t["domain"]): (t["correct"], t["seen"]) for t in profile["analytics"]["topics"]}
    assert topics == {("math", "Algebra"): (1, 2), ("math", "Geometry and Trigonometry"): (1, 1)}

    assert client.get("/api/users/9999", headers=auth_headers).status_code == 404


def test_the_leaderboard_ranks_best_attempts_by_score_then_time(client, auth_headers):
    fast_headers, _ = register(client, "Fast", "fast@example.com")
    slow_headers, _ = register(client, "Slow", "slow@example.com")
    attempt(client, auth_headers, score=600, time_spent=2000)
    attempt(client, auth_headers, score=750, time_spent=2500)  # the best one counts
    attempt(client, fast_headers, score=750, time_spent=2100)
    attempt(client, slow_headers, score=750, time_spent=0)  # no time recorded: last among ties
    attempt(client, slow_headers, score=500, section="reading")

    board = client.get("/api/leaderboard?section=math").get_json()["leaderboard"]
    assert [(row["rank"], row["user"]["username"], row["score"]) for row in board] == [
        (1, "Fast", 750),
        (2, "Nika", 750),
        (3, "Slow", 750),
    ]
    assert board[0]["time_spent"] == 2100
    assert board[0]["user"]["tier"] == "elite"

    reading = client.get("/api/leaderboard?section=reading").get_json()["leaderboard"]
    assert [row["user"]["username"] for row in reading] == ["Slow"]
    assert client.get("/api/leaderboard?section=science").status_code == 422


def test_the_platform_numbers_come_from_the_tables(client, auth_headers):
    client.patch("/api/auth/profile", json={"location": "Tajikistan, Dushanbe"}, headers=auth_headers)
    other_headers, _ = register(client, "Amina", "amina@example.com")
    client.patch("/api/auth/profile", json={"location": "tajikistan, Khujand"}, headers=other_headers)
    attempt(client, auth_headers, score=800)
    attempt(client, other_headers, score=600)
    attempt(client, other_headers, score=700, section="reading")

    stats = client.get("/api/stats").get_json()
    assert stats["students"] == 2
    assert stats["tests_taken"] == 3
    assert stats["by_section"]["math"] == {"taken": 2, "average": 700, "perfect_scorers": 1}
    assert stats["by_section"]["reading"]["taken"] == 1
    assert stats["countries"][0]["flag"] == "🇹🇯"
    assert stats["countries"][0]["students"] == 2


def test_a_specific_test_can_be_retaken(client):
    response = client.get("/api/tests/module-1?section=math&test_id=bundle-1")
    assert response.status_code == 200
    assert response.get_json()["test_id"] == "bundle-1"
    assert client.get("/api/tests/module-1?section=reading&test_id=bundle-1").status_code == 404
    assert client.get("/api/tests/module-1?test_id=nope").status_code == 404
