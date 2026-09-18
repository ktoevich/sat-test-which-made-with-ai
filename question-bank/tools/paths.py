"""Where the question-bank files live, relative to this checkout."""

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

LOOKUP = ROOT / "lookup.json"
LIST = ROOT / "questions-list.json"
QUESTIONS = ROOT / "questions.jsonl"
INDEX = ROOT / "questions-index.json"

API = "https://qbank-api.collegeboard.org/msreportingquestionbank-prod/questionbank"
ORIGIN = "https://satsuiteeducatorquestionbank.collegeboard.org"

HEADERS = {
    "Content-Type": "application/json",
    "Accept": "application/json, text/plain, */*",
    "Origin": ORIGIN,
    "Referer": ORIGIN + "/",
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
    ),
}
