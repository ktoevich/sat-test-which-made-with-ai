"""Reads a question export you already have on disk and normalises it.

The importer is deliberately format-agnostic: it accepts a flat JSON array or a
CSV of questions and maps common column names onto this project's fields. It
does not download anything — point it at a file you exported yourself.
"""

from __future__ import annotations

import csv
import hashlib
import json
import re
from pathlib import Path
from typing import Any, Iterable

from .schema import DIFFICULTIES, QUESTION_TYPES, option_letter, validate_question

Question = dict[str, Any]

#: Source column -> field in this project. Keys are compared lower-cased with
#: spaces, dashes and underscores stripped.
FIELD_ALIASES = {
    "questionid": "question_id",
    "id": "question_id",
    "externalid": "question_id",
    "uid": "question_id",
    "type": "type",
    "questiontype": "type",
    "format": "type",
    "difficulty": "difficulty",
    "level": "difficulty",
    "text": "text",
    "question": "text",
    "stem": "text",
    "prompt": "text",
    "body": "text",
    "answer": "answer",
    "correctanswer": "answer",
    "correct": "answer",
    "key": "answer",
    "rationale": "rationale",
    "explanation": "rationale",
    "solution": "rationale",
    "skill": "skill",
    "skilldescription": "skill",
    "domain": "domain",
    "category": "domain",
    "options": "options",
    "choices": "choices",
    "answerchoices": "choices",
    "image": "image",
    "figure": "image",
    "svg": "image",
}

TYPE_ALIASES = {
    "mcq": "MCQ",
    "multiplechoice": "MCQ",
    "multiplechoicequestion": "MCQ",
    "choice": "MCQ",
    "spr": "SPR",
    "studentproducedresponse": "SPR",
    "gridin": "SPR",
    "freeresponse": "SPR",
    "numeric": "SPR",
}

DIFFICULTY_ALIASES = {
    "e": "Easy",
    "easy": "Easy",
    "1": "Easy",
    "m": "Medium",
    "medium": "Medium",
    "moderate": "Medium",
    "2": "Medium",
    "h": "Hard",
    "hard": "Hard",
    "difficult": "Hard",
    "3": "Hard",
}

OPTION_SPLIT = re.compile(r"\s*\|\s*|\s*;;\s*")
# Matches per-choice columns like "option_a" / "optionB", but not the word "options".
OPTION_COLUMN = re.compile(r"^option[_\s-]?([a-h])$", re.IGNORECASE)

DEFAULT_DIFFICULTY = "Medium"


class ImportError_(ValueError):
    """Raised when a source row cannot be turned into a question."""


def _key(name: str) -> str:
    return re.sub(r"[\s_\-]", "", str(name)).lower()


def load_source(path: str | Path) -> list[dict[str, Any]]:
    """Read a `.json` or `.csv` export into a list of raw rows."""
    path = Path(path)
    if not path.is_file():
        raise ImportError_(f"source file not found: {path}")

    if path.suffix.lower() == ".csv":
        with path.open(encoding="utf-8-sig", newline="") as handle:
            return [dict(row) for row in csv.DictReader(handle)]

    with path.open(encoding="utf-8") as handle:
        data = json.load(handle)

    if isinstance(data, dict):
        # Some exports wrap the list, e.g. {"questions": [...]}.
        for candidate in ("questions", "items", "data", "results"):
            if isinstance(data.get(candidate), list):
                return data[candidate]
        raise ImportError_(
            "JSON object has no list under 'questions', 'items', 'data' or 'results'"
        )
    if not isinstance(data, list):
        raise ImportError_("JSON source must be a list of questions")
    return data


def _remap(row: dict[str, Any]) -> dict[str, Any]:
    """Rename known aliases and collect `option_a`-style columns."""
    mapped: dict[str, Any] = {}
    lettered: dict[str, str] = {}

    for name, value in row.items():
        match = OPTION_COLUMN.match(str(name))
        if match:
            if str(value).strip():
                lettered[match.group(1).upper()] = str(value).strip()
            continue
        field = FIELD_ALIASES.get(_key(name))
        if field and mapped.get(field) in (None, ""):
            mapped[field] = value

    if lettered:
        mapped.setdefault("choices", [lettered[letter] for letter in sorted(lettered)])
    return mapped


def _normalise_type(value: Any, has_options: bool) -> str:
    text = _key(value or "")
    if text in TYPE_ALIASES:
        return TYPE_ALIASES[text]
    if str(value).upper() in QUESTION_TYPES:
        return str(value).upper()
    return "MCQ" if has_options else "SPR"


def _normalise_difficulty(value: Any) -> str:
    text = str(value or "").strip().lower()
    if text in DIFFICULTY_ALIASES:
        return DIFFICULTY_ALIASES[text]
    title = text.title()
    return title if title in DIFFICULTIES else DEFAULT_DIFFICULTY


def _normalise_options(mapped: dict[str, Any]) -> list[str]:
    """Return options as ``["A) ...", "B) ...", ...]``, lettering them if needed."""
    raw = mapped.get("options") or mapped.get("choices") or []
    if isinstance(raw, str):
        raw = [part for part in OPTION_SPLIT.split(raw) if part.strip()]
    if not isinstance(raw, list):
        return []

    options: list[str] = []
    for index, item in enumerate(raw):
        if isinstance(item, dict):
            letter = str(item.get("letter") or item.get("label") or "").strip().upper()
            body = str(item.get("text") or item.get("content") or item.get("value") or "").strip()
        else:
            body = str(item).strip()
            letter = ""

        if not body:
            continue
        if not letter and option_letter(body):
            options.append(body)
            continue
        options.append(f"{letter or chr(ord('A') + index)}) {body}")
    return options


def _normalise_answer(value: Any, options: list[str]) -> str:
    """MCQ answers become a letter; grid-ins keep their literal value.

    Order matters: an answer that matches an option's *text* wins over reading
    it as an index, otherwise a numeric answer like "2" against the options
    1/2/3/4 would silently select the wrong choice.
    """
    answer = str(value if value is not None else "").strip()
    if not options:
        return answer

    letters = [option_letter(option) or "" for option in options]
    if answer.upper() in letters:
        return answer.upper()

    for letter, option in zip(letters, options):
        if option[3:].strip() == answer:
            return letter

    if answer.isdigit() and 0 <= int(answer) < len(letters):
        # Some exports store a zero-based index instead of a letter.
        return letters[int(answer)]

    return answer.upper()


def _normalise_image(value: Any) -> Any:
    if isinstance(value, dict):
        return value
    text = str(value or "").strip()
    if not text or text.lower() in {"null", "none", "nan"}:
        return None
    if text.startswith("{"):
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return text
    return text


def _fallback_id(text: str, answer: str) -> str:
    return hashlib.sha1(f"{text}|{answer}".encode()).hexdigest()[:8]


def normalise_question(row: dict[str, Any], *, index: int) -> Question:
    """Turn one source row into a question in this project's format."""
    mapped = _remap(row)

    text = str(mapped.get("text") or "").strip()
    if not text:
        raise ImportError_(f"row {index}: no question text (looked for text/question/stem/prompt)")

    options = _normalise_options(mapped)
    qtype = _normalise_type(mapped.get("type"), bool(options))
    answer = _normalise_answer(mapped.get("answer"), options if qtype == "MCQ" else [])

    if not answer:
        raise ImportError_(f"row {index}: no answer")

    question: Question = {
        "question_id": str(mapped.get("question_id") or _fallback_id(text, answer)).strip(),
        "domain": str(mapped.get("domain") or "").strip() or None,
        "skill": str(mapped.get("skill") or "").strip() or None,
        "difficulty": _normalise_difficulty(mapped.get("difficulty")),
        "type": qtype,
        "text": text,
        "answer": answer,
        "rationale": str(mapped.get("rationale") or "").strip() or None,
        "image": _normalise_image(mapped.get("image")),
    }
    if qtype == "MCQ":
        question["options"] = options
    return question


def import_questions(
    rows: Iterable[dict[str, Any]], *, skip_invalid: bool = False
) -> tuple[list[Question], list[str]]:
    """Normalise every row, rejecting the ones that cannot make a valid question.

    Each row is checked against the schema straight away, so a bad answer key is
    reported with its row number instead of surfacing much later as a broken
    bank. Rows repeating a ``question_id`` already seen are dropped.

    @returns the questions plus the problems found; failing rows are skipped when
    ``skip_invalid`` is set, and raise otherwise.
    """
    questions: list[Question] = []
    problems: list[str] = []
    seen_ids: set[str] = set()

    def reject(message: str) -> None:
        if not skip_invalid:
            raise ImportError_(message)
        problems.append(message)

    for index, row in enumerate(rows, start=1):
        try:
            question = normalise_question(row, index=index)
        except ImportError_ as error:
            reject(str(error))
            continue

        issues = validate_question(question, f"row {index}")
        if issues:
            reject(f"row {index}: " + "; ".join(str(issue) for issue in issues))
            continue

        question_id = str(question["question_id"])
        if question_id in seen_ids:
            reject(f"row {index}: duplicate question_id {question_id!r}")
            continue

        seen_ids.add(question_id)
        questions.append(question)

    return questions, problems
