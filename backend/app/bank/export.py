"""Renders a question bank as readable Markdown: papers, keys and solutions.

The output is meant to be read by a person — reviewing a generated bank, or
printing a paper — rather than parsed. `app.cli export` writes it out.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Iterable

from . import blueprint
from .schema import MODULE_KEYS, option_letter
from .taxonomy import DIFFICULTIES, DOMAINS

Question = dict[str, Any]
Bundle = dict[str, Any]


def _answer_text(question: Question) -> str:
    """The correct answer, with the full option text when there is one."""
    answer = str(question.get("answer", "")).strip()
    options = question.get("options")
    if not options:
        return answer

    for option in options:
        if (option_letter(option) or "").upper() == answer.upper():
            return f"{answer} — {option[3:].strip()}"
    return answer


def _figure(question: Question) -> list[str]:
    image = question.get("image")
    if isinstance(image, dict):
        return [
            f"*Figure: coordinate grid, x and y from "
            f"−{image.get('xEnd')} to {image.get('yEnd')}.*",
            "",
        ]
    if isinstance(image, str) and image and image != "null":
        return ["*Figure omitted from this export.*", ""]
    return []


def render_question(number: int, question: Question) -> str:
    """One question with its options, answer and solution."""
    domain = question.get("domain") or "—"
    skill = question.get("skill") or "—"
    difficulty = question.get("difficulty") or "—"

    lines = [
        f"#### {number}. {difficulty} · {domain}",
        f"*{skill}*",
        "",
        *_figure(question),
        str(question.get("text", "")).strip(),
        "",
    ]

    correct = str(question.get("answer", "")).strip().upper()
    for option in question.get("options") or []:
        letter = (option_letter(option) or "").upper()
        marker = "**" if letter == correct else ""
        lines.append(f"- {marker}{option}{marker}")
    if question.get("options"):
        lines.append("")

    lines.append(f"**Answer:** {_answer_text(question)}")
    lines.append("")

    rationale = str(question.get("rationale") or "").strip()
    if rationale:
        lines += [f"**Solution:** {rationale}", ""]

    return "\n".join(lines)


def render_module(key: str, questions: Iterable[Question]) -> str:
    questions = list(questions)
    counts = {
        level: sum(1 for q in questions if q.get("difficulty") == level)
        for level in DIFFICULTIES
    }
    spread = ", ".join(f"{level} {count}" for level, count in counts.items())
    grid_ins = sum(1 for q in questions if q.get("type") == "SPR")

    module = blueprint.BY_KEY.get(key)
    header = [f"## {module.title if module else key}", ""]
    if module:
        bands = "; ".join(f"{band.first}-{band.last} {band.label}" for band in module.bands)
        header += [module.description, "", f"In the exam, questions run {bands}.", ""]
    header += [
        f"{len(questions)} questions ({len(questions) - grid_ins} multiple choice, "
        f"{grid_ins} grid-ins) — {spread}.",
        "",
    ]
    return "\n".join(header + [render_question(i, q) for i, q in enumerate(questions, 1)])


def render_bundle(bundle: Bundle) -> str:
    """A whole test: all three modules, with answers and solutions inline."""
    parts = [
        f"# {bundle.get('test_id', 'Test')}",
        "",
        "Every question below is followed by its answer and worked solution, so "
        "this file is a paper and an answer key at once.",
        "",
        "Each attempt shows module 1 and then **one** of the two second modules, "
        "chosen by how the student did.",
        "",
    ]
    parts += [render_module(key, bundle.get(key, [])) for key in MODULE_KEYS]
    return "\n".join(parts).rstrip() + "\n"


def render_index(bank: list[Bundle], filenames: dict[str, str]) -> str:
    """A contents page linking to every test."""
    questions = [q for b in bank for key in MODULE_KEYS for q in b.get(key, [])]

    lines = [
        "# Test papers, answers and solutions",
        "",
        "Generated from `backend/data/tests_bundle_cache.json`. Rebuild with:",
        "",
        "```bash",
        "make export",
        "```",
        "",
        f"{len(bank)} test(s), {len(questions)} questions.",
        "",
        "| Test | Questions | File |",
        "| ---- | --------: | ---- |",
    ]
    for bundle in bank:
        test_id = bundle.get("test_id", "?")
        count = sum(len(bundle.get(key, [])) for key in MODULE_KEYS)
        lines.append(f"| {test_id} | {count} | [{filenames[test_id]}]({filenames[test_id]}) |")

    lines += ["", "## Coverage by domain", "", "| Domain | Questions | Share |", "| --- | ---: | ---: |"]
    total = len(questions) or 1
    for domain in DOMAINS:
        count = sum(1 for q in questions if q.get("domain") == domain.name)
        lines.append(f"| {domain.name} | {count} | {count / total:.0%} |")

    lines += ["", "## Coverage by difficulty", "", "| Difficulty | Questions |", "| --- | ---: |"]
    for level in DIFFICULTIES:
        lines.append(f"| {level} | {sum(1 for q in questions if q.get('difficulty') == level)} |")

    return "\n".join(lines) + "\n"


def export_bank(bank: list[Bundle], out_dir: str | Path) -> list[Path]:
    """Write one Markdown file per test plus a README index."""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    # Remove previous output so a smaller bank does not leave stale files behind.
    for stale in out_dir.glob("*.md"):
        stale.unlink()

    written: list[Path] = []
    filenames: dict[str, str] = {}

    for index, bundle in enumerate(bank, start=1):
        test_id = str(bundle.get("test_id") or f"test-{index:02d}")
        name = f"{test_id}.md"
        filenames[test_id] = name

        path = out_dir / name
        path.write_text(render_bundle(bundle), encoding="utf-8")
        written.append(path)

    index_path = out_dir / "README.md"
    index_path.write_text(render_index(bank, filenames), encoding="utf-8")
    written.append(index_path)

    return written
