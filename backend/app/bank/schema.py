"""Validation rules for a question bank file.

Implemented in plain Python rather than JSON Schema so the messages can point at
a concrete bundle and question, and so the project keeps zero runtime
dependencies beyond Flask.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable

from .taxonomy import DIFFICULTIES

QUESTION_TYPES = ("MCQ", "SPR")
MODULE_KEYS = ("module_1", "module_2_HIGHER", "module_2_LOWER")

REQUIRED_QUESTION_FIELDS = ("question_id", "type", "difficulty", "text", "answer")
IMAGE_FIELDS = ("xEnd", "yEnd", "step", "draw")

OPTION_SEPARATOR = ") "


@dataclass(frozen=True)
class Issue:
    """One validation problem, addressed by a dotted path into the file."""

    path: str
    message: str

    def __str__(self) -> str:
        return f"{self.path}: {self.message}"


class BankValidationError(ValueError):
    def __init__(self, issues: list[Issue]) -> None:
        super().__init__("\n".join(str(issue) for issue in issues))
        self.issues = issues


def option_letter(option: Any) -> str | None:
    """Return the leading letter of an ``"A) text"`` option, if it has one."""
    text = str(option)
    if len(text) < 3 or text[1:3] != OPTION_SEPARATOR:
        return None
    return text[0].upper()


def validate_question(question: Any, path: str) -> list[Issue]:
    issues: list[Issue] = []
    if not isinstance(question, dict):
        return [Issue(path, "must be an object")]

    for field in REQUIRED_QUESTION_FIELDS:
        if question.get(field) in (None, ""):
            issues.append(Issue(f"{path}.{field}", "is required"))

    qtype = question.get("type")
    if qtype is not None and qtype not in QUESTION_TYPES:
        issues.append(Issue(f"{path}.type", f"must be one of {QUESTION_TYPES}, got {qtype!r}"))

    difficulty = question.get("difficulty")
    if difficulty is not None and difficulty not in DIFFICULTIES:
        issues.append(
            Issue(f"{path}.difficulty", f"must be one of {DIFFICULTIES}, got {difficulty!r}")
        )

    if not isinstance(question.get("text", ""), str):
        issues.append(Issue(f"{path}.text", "must be a string"))

    if qtype == "MCQ":
        issues.extend(_validate_choices(question, path))
    elif qtype == "SPR" and question.get("options"):
        issues.append(Issue(f"{path}.options", "SPR questions must not carry options"))

    issues.extend(_validate_image(question.get("image"), f"{path}.image"))
    return issues


def _validate_choices(question: dict, path: str) -> list[Issue]:
    issues: list[Issue] = []
    options = question.get("options")

    if not isinstance(options, list) or len(options) < 2:
        return [Issue(f"{path}.options", "MCQ questions need a list of at least 2 options")]

    letters: list[str] = []
    for index, option in enumerate(options):
        letter = option_letter(option)
        if letter is None:
            issues.append(
                Issue(f"{path}.options[{index}]", 'must start with a letter and ")", e.g. "A) 12"')
            )
            continue
        if letter in letters:
            issues.append(Issue(f"{path}.options[{index}]", f"duplicate option letter {letter!r}"))
        letters.append(letter)

    answer = str(question.get("answer", "")).strip().upper()
    if letters and answer not in letters:
        issues.append(
            Issue(f"{path}.answer", f"{answer!r} is not one of the option letters {letters}")
        )
    return issues


def _validate_image(image: Any, path: str) -> list[Issue]:
    if image is None or isinstance(image, str):
        return []
    if not isinstance(image, dict):
        return [Issue(path, "must be null, an SVG string, or a coordinate-grid object")]

    issues = [Issue(f"{path}.{field}", "is required") for field in IMAGE_FIELDS if field not in image]
    for field in ("xEnd", "yEnd", "step"):
        value = image.get(field)
        if value is not None and (not isinstance(value, (int, float)) or value <= 0):
            issues.append(Issue(f"{path}.{field}", "must be a positive number"))
    return issues


def validate_bundle(bundle: Any, path: str) -> list[Issue]:
    if not isinstance(bundle, dict):
        return [Issue(path, "must be an object")]

    issues: list[Issue] = []
    if not str(bundle.get("test_id", "")).strip():
        issues.append(Issue(f"{path}.test_id", "is required"))

    seen_ids: set[str] = set()
    for key in MODULE_KEYS:
        section = bundle.get(key)
        if not isinstance(section, list) or not section:
            issues.append(Issue(f"{path}.{key}", "must be a non-empty list of questions"))
            continue

        for index, question in enumerate(section):
            question_path = f"{path}.{key}[{index}]"
            issues.extend(validate_question(question, question_path))
            if isinstance(question, dict):
                question_id = question.get("question_id")
                if question_id in seen_ids:
                    issues.append(
                        Issue(f"{question_path}.question_id", f"duplicate id {question_id!r}")
                    )
                elif question_id:
                    seen_ids.add(str(question_id))

    return issues


def validate_bank(data: Any) -> list[Issue]:
    """Return every problem found in a parsed bank file; empty means valid."""
    if not isinstance(data, list):
        return [Issue("$", "the bank file must contain a list of bundles")]
    if not data:
        return [Issue("$", "the bank file is empty")]

    issues: list[Issue] = []
    seen_test_ids: set[str] = set()
    for index, bundle in enumerate(data):
        path = f"$[{index}]"
        issues.extend(validate_bundle(bundle, path))
        if isinstance(bundle, dict):
            test_id = str(bundle.get("test_id", ""))
            if test_id and test_id in seen_test_ids:
                issues.append(Issue(f"{path}.test_id", f"duplicate test_id {test_id!r}"))
            seen_test_ids.add(test_id)
    return issues


def assert_valid(data: Any) -> None:
    """Raise :class:`BankValidationError` when ``data`` is not a valid bank."""
    issues = validate_bank(data)
    if issues:
        raise BankValidationError(issues)


def summarise(data: Iterable[dict]) -> dict[str, Any]:
    """Counts by module, type, difficulty and domain — used by the ``stats`` command."""
    totals: dict[str, Any] = {
        "bundles": 0,
        "questions": 0,
        "by_module": {},
        "by_type": {},
        "by_difficulty": {},
        "by_domain": {},
    }

    for bundle in data:
        totals["bundles"] += 1
        for key in MODULE_KEYS:
            for question in bundle.get(key, []) or []:
                totals["questions"] += 1
                _bump(totals["by_module"], key)
                _bump(totals["by_type"], question.get("type", "?"))
                _bump(totals["by_difficulty"], question.get("difficulty", "?"))
                _bump(totals["by_domain"], question.get("domain", "?"))
    return totals


def _bump(counter: dict[str, int], key: str) -> None:
    counter[key] = counter.get(key, 0) + 1
