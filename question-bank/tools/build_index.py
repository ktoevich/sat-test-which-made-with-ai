"""Fold the catalogue and the downloaded bodies into one index, with graphics.

questions-list.json holds one row per (assessment, question) and no question
text; questions.jsonl holds the bodies. This joins them into questions-index.json
-- one record per question, carrying its taxonomy and what visual it contains --
and prints the share of questions with a graph, by topic.

Questions not downloaded yet are kept in the index with "fetched": false rather
than dropped, so the index always accounts for the whole catalogue.
"""

from __future__ import annotations

import collections
import json
from datetime import date

from graphics import GRAPH_KINDS, describe
from paths import INDEX, LIST, QUESTIONS


def canonical_skills(rows: list[dict]) -> dict[str, str]:
    """Map each skill spelling to the one the bank uses most often.

    The catalogue carries a couple of casing slips -- "Cross-text Connections"
    against "Cross-Text Connections" -- which would otherwise split one skill
    into two topics in every count downstream.
    """
    spellings = collections.defaultdict(collections.Counter)
    for row in rows:
        skill = row.get("skill_desc")
        if skill:
            spellings[skill.lower()][skill] += 1
    return {
        spelling: variants.most_common(1)[0][0]
        for variants in spellings.values()
        for spelling in variants
    }


def load_catalogue() -> dict[str, dict]:
    """One record per question, merging its rows across the three assessments."""
    rows = json.loads(LIST.read_text())
    canonical = canonical_skills(rows)
    catalogue: dict[str, dict] = {}
    for row in rows:
        key = row.get("external_id") or row.get("ibn")
        if not key:
            continue
        record = catalogue.get(key)
        if record is None:
            record = catalogue[key] = {
                "id": key,
                "legacy": not row.get("external_id"),
                "questionId": row.get("questionId"),
                "assessments": [],
                # Difficulty is the one field that moves with the assessment: an
                # item can be hard on the PSAT 8/9 and easy on the SAT.
                "difficulty": {},
                "test": row["_test"],
                "domain": row.get("primary_class_cd_desc"),
                "domainCode": row.get("primary_class_cd"),
                "skill": canonical.get(row.get("skill_desc"), row.get("skill_desc")),
                "skillCode": row.get("skill_cd"),
            }
        if row["_asmt"] not in record["assessments"]:
            record["assessments"].append(row["_asmt"])
        record["difficulty"][row["_asmt"]] = row.get("difficulty")
    return catalogue


def load_bodies() -> dict[str, dict]:
    if not QUESTIONS.exists():
        return {}
    bodies = {}
    for line in QUESTIONS.open():
        try:
            row = json.loads(line)
        except ValueError:
            continue
        if "_error" not in row:
            bodies[row["_key"]] = row
    return bodies


def main() -> None:
    catalogue = load_catalogue()
    bodies = load_bodies()

    for key, record in catalogue.items():
        body = bodies.get(key)
        record["graphics"] = (
            {"fetched": False} if body is None else {"fetched": True, **describe(body)}
        )

    questions = sorted(
        catalogue.values(),
        key=lambda r: (r["test"], r["domain"] or "", r["skill"] or "", r["id"]),
    )
    fetched = [r for r in questions if r["graphics"]["fetched"]]
    with_graph = [r for r in fetched if r["graphics"]["graph"]]

    INDEX.write_text(json.dumps({
        "source": "https://satsuiteeducatorquestionbank.collegeboard.org/",
        "built": date.today().isoformat(),
        "counts": {
            "questions": len(questions),
            "bodiesFetched": len(fetched),
            "withGraph": len(with_graph),
        },
        "questions": questions,
    }, indent=1, ensure_ascii=False))

    print(f"{len(questions)} questions, {len(fetched)} bodies fetched, "
          f"{len(with_graph)} with a graph -> {INDEX.name}\n")
    report(fetched)


def report(fetched: list[dict]) -> None:
    """Print the share of questions carrying a graph, per topic."""
    topics = collections.defaultdict(
        lambda: {"n": 0, "graph": 0, "kinds": collections.Counter(), "table": 0}
    )
    for record in fetched:
        topic = topics[(record["test"], record["domain"], record["skill"])]
        topic["n"] += 1
        graphics = record["graphics"]
        if graphics["graph"]:
            topic["graph"] += 1
        if graphics["table"]:
            topic["table"] += 1
        for kind in graphics["kinds"]:
            topic["kinds"][kind] += 1

    header = f"{'graph%':>7}  {'graph/total':>12}  {'test':<4}  {'domain':<34}  {'skill':<52}  kinds"
    print(header)
    print("-" * len(header))
    for (test, domain, skill), t in sorted(
        topics.items(), key=lambda kv: (-kv[1]["graph"] / max(kv[1]["n"], 1), -kv[1]["n"])
    ):
        share = 100 * t["graph"] / t["n"]
        kinds = ", ".join(
            f"{k} {v}" for k, v in t["kinds"].most_common() if k in GRAPH_KINDS
        )
        print(f"{share:6.1f}%  {t['graph']:5}/{t['n']:<6}  {test:<4}  "
              f"{(domain or '')[:34]:<34}  {(skill or '')[:52]:<52}  {kinds}")


if __name__ == "__main__":
    main()
