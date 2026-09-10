import pytest

from app.bank import schema
from app.bank.schema import BankValidationError, assert_valid, summarise, validate_bank
from tests.conftest import make_question


def bundle_with(**overrides) -> dict:
    bundle = {
        "test_id": "b1",
        "module_1": [make_question("a", "MCQ", "Easy")],
        "module_2_HIGHER": [make_question("b", "MCQ", "Hard")],
        "module_2_LOWER": [make_question("c", "SPR", "Easy")],
    }
    bundle.update(overrides)
    return bundle


def paths(issues) -> list[str]:
    return [issue.path for issue in issues]


def test_a_well_formed_bank_has_no_issues():
    assert validate_bank([bundle_with()]) == []


def test_bank_must_be_a_non_empty_list():
    assert paths(validate_bank({})) == ["$"]
    assert paths(validate_bank([])) == ["$"]


def test_every_module_key_is_required():
    issues = validate_bank([bundle_with(module_2_LOWER=[])])
    assert "$[0].module_2_LOWER" in paths(issues)


def test_missing_required_question_fields_are_reported():
    broken = {"type": "MCQ", "difficulty": "Easy"}
    issues = validate_bank([bundle_with(module_1=[broken])])
    assert "$[0].module_1[0].question_id" in paths(issues)
    assert "$[0].module_1[0].text" in paths(issues)
    assert "$[0].module_1[0].answer" in paths(issues)


def test_unknown_type_and_difficulty_are_reported():
    question = make_question("x", "MCQ", "Easy") | {"type": "ESSAY", "difficulty": "Brutal"}
    issues = validate_bank([bundle_with(module_1=[question])])
    assert "$[0].module_1[0].type" in paths(issues)
    assert "$[0].module_1[0].difficulty" in paths(issues)


def test_options_must_be_lettered():
    question = make_question("x", "MCQ", "Easy") | {"options": ["just text", "B) fine"]}
    issues = validate_bank([bundle_with(module_1=[question])])
    assert "$[0].module_1[0].options[0]" in paths(issues)


def test_answer_must_match_an_option_letter():
    question = make_question("x", "MCQ", "Easy") | {"answer": "Z"}
    issues = validate_bank([bundle_with(module_1=[question])])
    assert "$[0].module_1[0].answer" in paths(issues)


def test_spr_questions_must_not_carry_options():
    question = make_question("x", "SPR", "Easy") | {"options": ["A) 1", "B) 2"]}
    issues = validate_bank([bundle_with(module_1=[question])])
    assert "$[0].module_1[0].options" in paths(issues)


def test_duplicate_question_ids_inside_a_bundle_are_reported():
    duplicate = make_question("same", "MCQ", "Easy")
    issues = validate_bank([bundle_with(module_1=[duplicate, dict(duplicate)])])
    assert any("duplicate id" in issue.message for issue in issues)


def test_duplicate_test_ids_are_reported():
    issues = validate_bank([bundle_with(), bundle_with()])
    assert any("duplicate test_id" in issue.message for issue in issues)


def test_image_descriptor_is_checked():
    question = make_question("x", "MCQ", "Easy") | {"image": {"xEnd": 0, "yEnd": 5, "step": 1}}
    issues = validate_bank([bundle_with(module_1=[question])])
    assert "$[0].module_1[0].image.draw" in paths(issues)
    assert "$[0].module_1[0].image.xEnd" in paths(issues)


def test_string_and_null_images_are_accepted():
    for image in (None, "<svg></svg>"):
        question = make_question("x", "MCQ", "Easy") | {"image": image}
        assert validate_bank([bundle_with(module_1=[question])]) == []


def test_assert_valid_raises_with_every_issue():
    with pytest.raises(BankValidationError) as error:
        assert_valid([{"test_id": ""}])
    assert error.value.issues


def test_option_letter_reads_the_prefix():
    assert schema.option_letter("C) 12") == "C"
    assert schema.option_letter("no letter") is None


def test_summarise_counts_by_dimension():
    counts = summarise([bundle_with()])
    assert counts["bundles"] == 1
    assert counts["questions"] == 3
    assert counts["by_type"] == {"MCQ": 2, "SPR": 1}
    assert counts["by_difficulty"] == {"Easy": 2, "Hard": 1}


def test_accepted_answers_must_be_a_usable_list():
    """A grid-in's alternative answers decide whether a student is marked right."""
    base = make_question("x", "SPR", "Easy")

    assert schema.validate_question(base | {"accepted_answers": ["1/4", "0.25"]}, "$") == []
    assert schema.validate_question(base | {"accepted_answers": None}, "$") == []

    for bad in ("1/4", [""], ["ok", "  "]):
        issues = schema.validate_question(base | {"accepted_answers": bad}, "$")
        assert any("accepted_answers" in issue.path for issue in issues), bad


def test_multiple_choice_answers_take_no_alternatives():
    question = make_question("x", "MCQ", "Easy") | {"accepted_answers": ["B"]}
    issues = schema.validate_question(question, "$")
    assert any("accepted_answers" in issue.path for issue in issues)
