import json

import pytest

from app.bank.importer import ImportError_, import_questions, load_source, normalise_question


def test_json_list_is_read_directly(tmp_path):
    path = tmp_path / "export.json"
    path.write_text(json.dumps([{"text": "a"}]), encoding="utf-8")
    assert load_source(path) == [{"text": "a"}]


def test_json_object_is_unwrapped(tmp_path):
    path = tmp_path / "export.json"
    path.write_text(json.dumps({"questions": [{"text": "a"}]}), encoding="utf-8")
    assert load_source(path) == [{"text": "a"}]


def test_csv_is_read_as_rows(tmp_path):
    path = tmp_path / "export.csv"
    path.write_text("question,answer\nWhat is 2+2?,4\n", encoding="utf-8")
    assert load_source(path) == [{"question": "What is 2+2?", "answer": "4"}]


def test_missing_file_is_reported(tmp_path):
    with pytest.raises(ImportError_, match="not found"):
        load_source(tmp_path / "nope.json")


def test_aliases_are_mapped_onto_project_fields():
    row = {
        "External ID": "abc123",
        "Stem": "What is $2 + 2$?",
        "Answer Choices": ["4", "5", "6", "7"],
        "Correct Answer": "4",
        "Level": "e",
        "Skill Description": "Arithmetic",
        "Category": "Algebra",
        "Explanation": "Add them.",
    }
    question = normalise_question(row, index=1)

    assert question["question_id"] == "abc123"
    assert question["type"] == "MCQ"
    assert question["difficulty"] == "Easy"
    assert question["skill"] == "Arithmetic"
    assert question["domain"] == "Algebra"
    assert question["rationale"] == "Add them."
    assert question["options"] == ["A) 4", "B) 5", "C) 6", "D) 7"]
    assert question["answer"] == "A"


def test_lettered_options_are_kept_as_they_are():
    row = {"text": "q", "options": ["B) two", "A) one"], "answer": "B"}
    question = normalise_question(row, index=1)
    assert question["options"] == ["B) two", "A) one"]
    assert question["answer"] == "B"


def test_pipe_separated_options_are_split_and_lettered():
    row = {"text": "q", "choices": "one | two | three | four", "answer": "two"}
    question = normalise_question(row, index=1)
    assert question["options"] == ["A) one", "B) two", "C) three", "D) four"]
    assert question["answer"] == "B"


def test_option_columns_are_collected():
    row = {"text": "q", "option_a": "one", "option_b": "two", "answer": "1"}
    question = normalise_question(row, index=1)
    assert question["options"] == ["A) one", "B) two"]
    # A zero-based index selects the second option.
    assert question["answer"] == "B"


def test_option_objects_use_their_own_letters():
    row = {
        "text": "q",
        "options": [{"letter": "A", "text": "one"}, {"label": "B", "content": "two"}],
        "answer": "A",
    }
    assert normalise_question(row, index=1)["options"] == ["A) one", "B) two"]


def test_type_is_inferred_when_absent():
    assert normalise_question({"text": "q", "answer": "12"}, index=1)["type"] == "SPR"
    assert normalise_question(
        {"text": "q", "answer": "A", "options": ["A) 1", "B) 2"]}, index=1
    )["type"] == "MCQ"


def test_grid_in_answers_are_kept_verbatim():
    question = normalise_question({"text": "q", "type": "grid-in", "answer": "3/4"}, index=1)
    assert question["type"] == "SPR"
    assert question["answer"] == "3/4"
    assert "options" not in question


def test_unknown_difficulty_falls_back_to_medium():
    assert normalise_question({"text": "q", "answer": "1", "level": "?"}, index=1)["difficulty"] == "Medium"


def test_image_json_string_is_parsed():
    row = {"text": "q", "answer": "1", "figure": '{"xEnd": 5, "yEnd": 5, "step": 1, "draw": ""}'}
    assert normalise_question(row, index=1)["image"]["xEnd"] == 5


def test_placeholder_images_become_null():
    for value in ("", "null", "NaN"):
        assert normalise_question({"text": "q", "answer": "1", "image": value}, index=1)["image"] is None


def test_missing_text_is_rejected():
    with pytest.raises(ImportError_, match="no question text"):
        normalise_question({"answer": "1"}, index=4)


def test_question_id_falls_back_to_a_hash_of_the_content():
    first = normalise_question({"text": "q", "answer": "1"}, index=1)
    second = normalise_question({"text": "q", "answer": "1"}, index=2)
    assert first["question_id"] == second["question_id"]
    assert len(first["question_id"]) == 8


def test_skip_invalid_collects_problems_instead_of_raising():
    rows = [{"text": "good", "answer": "1"}, {"answer": "no text"}]
    questions, problems = import_questions(rows, skip_invalid=True)
    assert len(questions) == 1
    assert len(problems) == 1

    with pytest.raises(ImportError_):
        import_questions(rows)
