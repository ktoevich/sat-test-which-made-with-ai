import json

import pytest

from app.bank import schema
from app.cli import main


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def test_generate_writes_a_valid_bank(tmp_path, capsys):
    output = tmp_path / "bank.json"
    assert main(["generate", "--bundles", "2", "--module-size", "8", "--spr", "2",
                 "--seed", "1", "-o", str(output)]) == 0

    bank = read(output)
    assert schema.validate_bank(bank) == []
    assert len(bank) == 2
    assert len(bank[0]["module_1"]) == 8
    assert "wrote 2 bundle(s)" in capsys.readouterr().out


def test_generate_refuses_to_clobber_an_existing_file(tmp_path):
    output = tmp_path / "bank.json"
    output.write_text("keep me", encoding="utf-8")

    with pytest.raises(SystemExit, match="--force"):
        main(["generate", "-o", str(output), "--module-size", "6", "--spr", "2"])
    assert output.read_text(encoding="utf-8") == "keep me"


def test_force_overwrites(tmp_path):
    output = tmp_path / "bank.json"
    output.write_text("replace me", encoding="utf-8")

    assert main(["generate", "--module-size", "6", "--spr", "2", "--seed", "2",
                 "-o", str(output), "--force"]) == 0
    assert isinstance(read(output), list)


def test_generate_is_reproducible_with_a_seed(tmp_path):
    first, second = tmp_path / "a.json", tmp_path / "b.json"
    for output in (first, second):
        main(["generate", "--module-size", "6", "--spr", "2", "--seed", "99", "-o", str(output)])
    assert read(first) == read(second)


def test_validate_accepts_a_generated_bank(tmp_path, capsys):
    output = tmp_path / "bank.json"
    main(["generate", "--module-size", "6", "--spr", "2", "--seed", "3", "-o", str(output)])

    assert main(["validate", "--bank", str(output)]) == 0
    assert "valid" in capsys.readouterr().out


def test_validate_reports_problems_and_exits_nonzero(tmp_path, capsys):
    bad = tmp_path / "bad.json"
    bad.write_text(json.dumps([{"test_id": "x", "module_1": []}]), encoding="utf-8")

    assert main(["validate", "--bank", str(bad)]) == 1
    assert "problem(s)" in capsys.readouterr().err


def test_validate_rejects_broken_json(tmp_path):
    bad = tmp_path / "bad.json"
    bad.write_text("{not json", encoding="utf-8")
    with pytest.raises(SystemExit, match="not valid JSON"):
        main(["validate", "--bank", str(bad)])


def test_stats_summarises_a_bank(tmp_path, capsys):
    output = tmp_path / "bank.json"
    main(["generate", "--bundles", "1", "--module-size", "6", "--spr", "2",
          "--seed", "5", "-o", str(output)])
    capsys.readouterr()

    assert main(["stats", "--bank", str(output)]) == 0
    out = capsys.readouterr().out
    assert "18 questions" in out
    assert "difficulty" in out


def test_import_builds_a_bank_from_a_csv(tmp_path, capsys):
    source = tmp_path / "export.csv"
    rows = ["question,answer,difficulty,type,option_a,option_b,option_c,option_d"]
    for index in range(24):
        rows.append(f"Question {index}?,A,Easy,MCQ,one{index},two{index},three{index},four{index}")
    for index in range(12):
        rows.append(f"Grid-in {index}?,{index},Medium,SPR,,,,")
    source.write_text("\n".join(rows) + "\n", encoding="utf-8")

    output = tmp_path / "bank.json"
    assert main(["import", str(source), "--module-size", "6", "--spr", "2",
                 "--seed", "4", "-o", str(output)]) == 0

    assert "read 36 question(s)" in capsys.readouterr().out
    bank = read(output)
    assert schema.validate_bank(bank) == []
    assert bank[0]["test_id"] == "sat-imported-01"


def test_import_fails_when_the_source_is_too_small(tmp_path):
    source = tmp_path / "export.json"
    source.write_text(json.dumps([{"text": "q", "answer": "1"}]), encoding="utf-8")

    with pytest.raises(SystemExit, match="need"):
        main(["import", str(source), "-o", str(tmp_path / "out.json")])


def test_import_can_skip_unusable_rows(tmp_path, capsys):
    source = tmp_path / "export.json"
    rows = [{"text": f"Q{i}", "answer": str(i), "difficulty": "Easy"} for i in range(9)]
    rows.append({"answer": "no text here"})
    source.write_text(json.dumps(rows), encoding="utf-8")

    assert main(["import", str(source), "--skip-invalid", "--module-size", "3", "--spr", "1",
                 "--seed", "1", "-o", str(tmp_path / "out.json")]) == 0
    assert "skipped:" in capsys.readouterr().err
