"""A practice set: a few questions of one domain, with their answers."""


def test_a_practice_set_is_drawn_from_the_bank_by_domain(client, bundle):
    response = client.get("/api/practice?section=math&count=2")
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["section"] == "math"
    assert len(payload["questions"]) == 2
    assert [q["id"] for q in payload["questions"]] == [1, 2]
    assert all("answer" in q for q in payload["questions"]), "answers travel, for instant checking"

    ids = {q["question_id"] for b in [bundle] for k in ("module_1", "module_2_HIGHER", "module_2_LOWER") for q in b[k]}
    assert {q["question_id"] for q in payload["questions"]} <= ids


def test_a_reading_practice_set_filters_by_domain(client):
    response = client.get("/api/practice?section=reading&domain=Craft%20and%20Structure&count=5")
    assert response.status_code == 200
    questions = response.get_json()["questions"]
    assert questions and all(q["domain"] == "Craft and Structure" for q in questions)
    assert all(q["passage"] for q in questions)


def test_practice_rejects_a_domain_of_the_other_section(client):
    assert client.get("/api/practice?section=math&domain=Craft%20and%20Structure").status_code == 422
    assert client.get("/api/practice?section=history").status_code == 422
