"""Write the math tests of the question bank into ``questions.js``.

The standalone test is opened straight from disk, where a page may not fetch a
JSON file, so the tests travel as a script that sets ``window.SAT_TESTS``.

    python3 standalone-test/build.py
    python3 standalone-test/build.py --bank path/to/tests_bundle_cache.json
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
DEFAULT_BANK = HERE.parent / "backend" / "data" / "tests_bundle_cache.json"
MODULES = ("module_1", "module_2_HIGHER", "module_2_LOWER")
#: What the page reads from a question; the rest of the bank's fields stay behind.
FIELDS = (
    "question_id", "domain", "skill", "difficulty", "type",
    "text", "options", "answer", "accepted_answers", "rationale", "image",
)


def build(bank: Path) -> list[dict]:
    tests = []
    for bundle in json.loads(bank.read_text(encoding="utf-8")):
        if bundle.get("section", "math") != "math":
            continue
        test = {"id": bundle["test_id"]}
        for module in MODULES:
            test[module] = [
                {field: question[field] for field in FIELDS if question.get(field) not in (None, "", [])}
                for question in bundle[module]
            ]
        tests.append(test)
    return tests


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--bank", type=Path, default=DEFAULT_BANK, help="the bank file to read")
    parser.add_argument("-o", "--output", type=Path, default=HERE / "questions.js")
    args = parser.parse_args()

    tests = build(args.bank)
    if not tests:
        raise SystemExit(f"{args.bank}: no math tests")
    payload = json.dumps(tests, ensure_ascii=False, separators=(",", ":"))
    # "</script" inside a string would still end an inline script; escape it
    # in case the file is ever inlined.
    payload = payload.replace("</", "<\\/")
    args.output.write_text(f"window.SAT_TESTS = {payload};\n", encoding="utf-8")
    print(f"{len(tests)} math tests -> {args.output} ({args.output.stat().st_size // 1024} KB)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
