"""Render questions-index.json as a readable report — report.html.

The page answers one question: which topics put a graph in front of the student.
It is built from whatever the index holds, so it can be regenerated at any point
during a download and will simply cover more of the bank each time; skills with
no bodies read yet stay in the table rather than vanishing from it.
"""

from __future__ import annotations

import collections
import json
from pathlib import Path

from graphics import GRAPH_KINDS
from paths import INDEX, ROOT

TEMPLATE = Path(__file__).with_name("report_template.html")
REPORT = ROOT / "report.html"


def summarise(index: dict) -> dict:
    questions = index["questions"]

    skills: dict[tuple, dict] = {}
    for q in questions:
        key = (q["test"], q["domain"], q["skill"])
        skill = skills.get(key)
        if skill is None:
            skill = skills[key] = {
                "test": q["test"], "domain": q["domain"], "skill": q["skill"],
                "catalogue": 0, "fetched": 0, "graph": 0, "kinds": collections.Counter(),
            }
        skill["catalogue"] += 1
        graphics = q["graphics"]
        if not graphics["fetched"]:
            continue
        skill["fetched"] += 1
        if graphics["graph"]:
            skill["graph"] += 1
        for kind in graphics["kinds"]:
            skill["kinds"][kind] += 1

    kinds = collections.Counter()
    tables = 0
    sample_label = None
    for q in questions:
        graphics = q["graphics"]
        if not graphics["fetched"]:
            continue
        tables += bool(graphics["table"])
        for kind in graphics["kinds"]:
            kinds[kind] += 1
        # A real label from the bank, shown in the method note so the reader can
        # see exactly what the classification reads. Prefer a graph's own label.
        if sample_label is None:
            for figure in graphics["figures"]:
                if figure["kind"] in GRAPH_KINDS and figure["label"]:
                    sample_label = figure["label"]
                    break

    fetched = [q for q in questions if q["graphics"]["fetched"]]
    unread = len(questions) - len(fetched)
    caveat = (
        f"{unread:,} questions are still to be read, and the download order works "
        "through Reading and Writing before Math, so the Math topics — where "
        "coordinate-plane graphs and geometric figures live — are the least covered "
        "so far. Treat any topic whose bodies are unread as unknown, not as "
        "graph-free."
    ) if unread else (
        "Every question in the bank has been read, so the shares above are the "
        "whole picture rather than a sample."
    )

    return {
        "built": index["built"],
        "source": index["source"],
        "totals": {
            "catalogue": len(questions),
            "fetched": len(fetched),
            "graph": sum(1 for q in fetched if q["graphics"]["graph"]),
            "table": tables,
            "rw": sum(1 for q in questions if q["test"] == "R&W"),
            "math": sum(1 for q in questions if q["test"] == "Math"),
        },
        "domains": len({(q["test"], q["domain"]) for q in questions}),
        "measuredSkills": sum(1 for s in skills.values() if s["fetched"]),
        "graphKinds": sorted(GRAPH_KINDS),
        "kinds": kinds.most_common(),
        "sampleLabel": sample_label,
        "caveat": caveat,
        "skills": [{**s, "kinds": dict(s["kinds"].most_common())} for s in skills.values()],
    }


def main() -> None:
    data = summarise(json.loads(INDEX.read_text()))
    payload = json.dumps(data, ensure_ascii=False).replace("</", "<\\/")
    REPORT.write_text(TEMPLATE.read_text().replace("__DATA__", payload))
    totals = data["totals"]
    print(f"{REPORT.name}: {totals['fetched']:,} of {totals['catalogue']:,} questions read, "
          f"{totals['graph']:,} with a graph")


if __name__ == "__main__":
    main()
