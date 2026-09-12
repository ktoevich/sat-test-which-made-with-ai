import json
import random

from app.bank import blueprint, exam_order, generate_bank, is_exam_order, order_bank
from app.bank.assembler import assemble_bank
from app.bank.schema import MODULE_KEYS
from app.cli import main
from tests.conftest import make_question


def _bands_of(module_key: str) -> list[str]:
    """The difficulty the blueprint expects at every question number."""
    module = blueprint.BY_KEY[module_key]
    return [band.difficulty for band in module.bands for _ in range(band.count)]


def test_exam_order_is_easy_then_medium_then_hard_and_stable():
    questions = [
        make_question("h1", "MCQ", "Hard"),
        make_question("e1", "SPR", "Easy"),
        make_question("m1", "MCQ", "Medium"),
        make_question("e2", "MCQ", "Easy"),
        make_question("h2", "SPR", "Hard"),
    ]
    assert [q["question_id"] for q in exam_order(questions)] == ["e1", "e2", "m1", "h1", "h2"]
    assert is_exam_order(exam_order(questions))
    assert not is_exam_order(questions)


def test_an_assembled_bundle_follows_the_bands_by_question_number():
    pool = [
        make_question(f"{qtype}-{difficulty}-{i}", qtype, difficulty)
        for qtype in ("MCQ", "SPR")
        for difficulty in ("Easy", "Medium", "Hard")
        for i in range(40)
    ]
    (bundle,) = assemble_bank(pool, bundles=1, rng=random.Random(3))

    for key in MODULE_KEYS:
        assert [q["difficulty"] for q in bundle[key]] == _bands_of(key), key


def test_a_generated_bundle_follows_the_bands_by_question_number():
    (bundle,) = generate_bank(bundles=1, rng=random.Random(5))

    for key in MODULE_KEYS:
        assert [q["difficulty"] for q in bundle[key]] == _bands_of(key), key


def test_order_bank_moves_only_what_is_out_of_order(bundle):
    already_sorted = {**bundle, "test_id": "sorted", "module_1": exam_order(bundle["module_1"])}
    bank = [bundle, already_sorted]

    assert order_bank(bank) == 1
    assert [q["question_id"] for q in bundle["module_1"]] == ["m1-easy", "m1-spr", "m1-hard"]
    assert order_bank(bank) == 0


def test_reorder_command_rewrites_the_bank_in_place(tmp_path, bundle, capsys):
    path = tmp_path / "bank.json"
    path.write_text(json.dumps([bundle]), encoding="utf-8")

    assert main(["reorder", "--bank", str(path)]) == 0
    assert "reordered 1 module(s)" in capsys.readouterr().out

    stored = json.loads(path.read_text(encoding="utf-8"))
    assert [q["difficulty"] for q in stored[0]["module_1"]] == ["Easy", "Medium", "Hard"]

    assert main(["reorder", "--bank", str(path)]) == 0
    assert "already in exam order" in capsys.readouterr().out
