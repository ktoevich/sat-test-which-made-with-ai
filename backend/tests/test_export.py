from app.bank.export import export_bank, render_bundle, render_question
from tests.conftest import make_question


def test_a_question_carries_its_prompt_answer_and_solution():
    question = make_question("q1", "MCQ", "Easy") | {
        "text": "What is $2 + 2$?",
        "answer": "B",
        "options": ["A) 3", "B) 4", "C) 5", "D) 6"],
        "rationale": "Add them.",
        "domain": "Algebra",
        "skill": "Linear equations in one variable",
    }
    rendered = render_question(7, question)

    assert "#### 7. Easy · Algebra" in rendered
    assert "Linear equations in one variable" in rendered
    assert "What is $2 + 2$?" in rendered
    assert "**Answer:** B — 4" in rendered
    assert "**Solution:** Add them." in rendered


def test_the_correct_option_is_the_only_one_marked():
    question = make_question("q1", "MCQ", "Easy") | {
        "answer": "C",
        "options": ["A) 3", "B) 4", "C) 5", "D) 6"],
    }
    rendered = render_question(1, question)

    assert "- **C) 5**" in rendered
    assert "- A) 3" in rendered
    assert "**A) 3**" not in rendered


def test_grid_in_questions_render_without_options():
    question = make_question("q1", "SPR", "Medium") | {"answer": "42", "options": None}
    rendered = render_question(1, question)

    assert "**Answer:** 42" in rendered
    assert "- A)" not in rendered


def test_a_coordinate_grid_is_described_rather_than_embedded():
    question = make_question("q1", "MCQ", "Easy") | {
        "image": {"xEnd": 8, "yEnd": 8, "step": 2, "draw": "<line/>"}
    }
    assert "coordinate grid" in render_question(1, question)
    assert "<line/>" not in render_question(1, question)


def test_a_bundle_renders_all_three_modules(bundle):
    rendered = render_bundle(bundle)

    assert "# bundle-1" in rendered
    assert "## Module 1" in rendered
    assert "## Module 2 — Higher" in rendered
    assert "## Module 2 — Lower" in rendered
    assert "questions run 1-7 Easy; 8-15 Medium; 16-22 Hard" in rendered
    assert "3 questions (2 multiple choice, 1 grid-ins)" in rendered


def test_export_writes_one_file_per_test_plus_an_index(tmp_path, bundle):
    written = export_bank([bundle], tmp_path)

    assert {path.name for path in written} == {"bundle-1.md", "README.md"}
    index = (tmp_path / "README.md").read_text(encoding="utf-8")
    assert "1 test(s), 5 questions" in index
    assert "[bundle-1.md](bundle-1.md)" in index


def test_export_clears_stale_files_from_a_previous_run(tmp_path, bundle):
    (tmp_path / "old-test.md").write_text("stale", encoding="utf-8")
    export_bank([bundle], tmp_path)

    assert not (tmp_path / "old-test.md").exists()


def test_the_index_reports_domain_coverage(tmp_path, bundle):
    export_bank([bundle], tmp_path)
    index = (tmp_path / "README.md").read_text(encoding="utf-8")

    assert "## Coverage by domain" in index
    assert "## Coverage by difficulty" in index
