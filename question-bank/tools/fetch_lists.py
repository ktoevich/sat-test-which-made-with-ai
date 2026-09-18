"""Download the question catalogue: every question the bank lists, with its taxonomy.

One row per (assessment, question); a question offered on both the SAT and a PSAT
appears once per assessment. Writes questions-list.json and lookup.json.
"""

from __future__ import annotations

import json
import urllib.request

from paths import API, HEADERS, LIST, LOOKUP

ASSESSMENTS = {99: "SAT", 100: "PSAT/NMSQT & PSAT 10", 102: "PSAT 8/9"}
TESTS = {1: "R&W", 2: "Math"}
#: The domain codes each test is filtered by, as the site's own search sends them.
DOMAINS = {1: "INI,CAS,EOI,SEC", 2: "H,P,Q,S"}


def post(path: str, body: dict):
    req = urllib.request.Request(f"{API}/{path}", json.dumps(body).encode(), HEADERS)
    return json.load(urllib.request.urlopen(req, timeout=120))


def main() -> None:
    req = urllib.request.Request(f"{API}/lookup", headers=HEADERS)
    LOOKUP.write_text(json.dumps(json.load(urllib.request.urlopen(req, timeout=60)), indent=1))
    print(f"lookup.json written")

    rows = []
    for asmt_id, asmt in ASSESSMENTS.items():
        for test_id, test in TESTS.items():
            data = post(
                "digital/get-questions",
                {"asmtEventId": asmt_id, "test": test_id, "domain": DOMAINS[test_id]},
            )
            for row in data:
                row["_asmt"] = asmt
                row["_test"] = test
            print(f"{asmt:22} {test:5} {len(data)}")
            rows += data

    LIST.write_text(json.dumps(rows))
    unique = {r.get("external_id") or r.get("ibn") for r in rows} - {None, ""}
    print(f"{len(rows)} rows, {len(unique)} unique questions -> {LIST.name}")


if __name__ == "__main__":
    main()
