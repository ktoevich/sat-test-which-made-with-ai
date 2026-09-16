"""What students see of each other: profiles, the leaderboard, the platform's numbers.

Everything here is read from the tables the app already keeps — no seeded
users, no invented traffic. A public profile is the other student's account
without its private fields, their attempts without the per-question
breakdowns, and the analytics the dashboard draws: the rating after every
test and how many questions of each domain they have got right.
"""

from __future__ import annotations

import json
import re
from collections import Counter
from typing import Any, Mapping

from ..bank.taxonomy import DEFAULT_SECTION, SECTIONS, SECTION_KEYS, section_of
from ..db import Database
from . import accounts, attempts as attempts_service, ratings, social

MAX_SEARCH_RESULTS = 20
MAX_LEADERBOARD = 100

#: Flags for the countries students write first in "Country, City".
COUNTRY_FLAGS = {
    "tajikistan": "🇹🇯", "таджикистан": "🇹🇯",
    "uzbekistan": "🇺🇿", "узбекистан": "🇺🇿",
    "kazakhstan": "🇰🇿", "казахстан": "🇰🇿",
    "kyrgyzstan": "🇰🇬", "кыргызстан": "🇰🇬", "киргизия": "🇰🇬",
    "russia": "🇷🇺", "россия": "🇷🇺",
    "belarus": "🇧🇾", "беларусь": "🇧🇾",
    "ukraine": "🇺🇦", "украина": "🇺🇦",
    "usa": "🇺🇸", "united states": "🇺🇸", "сша": "🇺🇸",
    "canada": "🇨🇦", "канада": "🇨🇦",
    "uk": "🇬🇧", "united kingdom": "🇬🇧", "великобритания": "🇬🇧",
    "germany": "🇩🇪", "германия": "🇩🇪",
    "turkey": "🇹🇷", "türkiye": "🇹🇷", "турция": "🇹🇷",
    "south korea": "🇰🇷", "korea": "🇰🇷", "южная корея": "🇰🇷",
    "china": "🇨🇳", "китай": "🇨🇳",
    "india": "🇮🇳", "индия": "🇮🇳",
    "azerbaijan": "🇦🇿", "азербайджан": "🇦🇿",
    "armenia": "🇦🇲", "армения": "🇦🇲",
    "georgia": "🇬🇪", "грузия": "🇬🇪",
}


# -- search and profiles -----------------------------------------------------


def search_users(db: Database, query: str, *, limit: int = 8) -> list[dict[str, Any]]:
    """Students whose handle or name contains ``query``, best rated first."""
    text = " ".join(str(query or "").split())
    limit = max(1, min(MAX_SEARCH_RESULTS, int(limit)))
    params: list[Any] = []
    where = "WHERE is_disabled = 0"
    if text:
        like = f"%{text}%"
        where += " AND (username LIKE ? OR full_name LIKE ?)"
        params += [like, like]
    params.append(limit)
    rows = db.fetch_all(
        f"SELECT * FROM users {where} ORDER BY rating DESC, username ASC LIMIT ?", params
    )
    return [accounts.User.from_row(row).public_dict() for row in rows]


def _summary(history: list[dict[str, Any]]) -> dict[str, Any]:
    """The numbers a profile card shows, from a list of attempt summaries."""
    by_section: dict[str, dict[str, Any]] = {}
    for key in SECTION_KEYS:
        own = [a for a in history if a["section"] == key]
        scores = [a["score"] for a in own]
        by_section[key] = {
            "taken": len(own),
            "best": max(scores) if scores else None,
            "average": round(sum(scores) / len(scores)) if scores else None,
        }
    scores = [a["score"] for a in history]
    return {
        "taken": len(history),
        "best": max(scores) if scores else None,
        "average": round(sum(scores) / len(scores)) if scores else None,
        "by_section": by_section,
    }


def public_profile(db: Database, viewer_id: int, user_id: int) -> dict[str, Any] | None:
    """Another student's page: profile, numbers, history without breakdowns, analytics."""
    row = db.fetch_one("SELECT * FROM users WHERE id = ? AND is_disabled = 0", (user_id,))
    if row is None:
        return None
    user = accounts.User.from_row(row)
    history = attempts_service.list_summaries(db, user_id)
    return {
        "user": user.public_dict(),
        "summary": _summary(history),
        "history": history,
        "analytics": analytics(db, user_id),
        "friends_count": social.friends_count(db, user_id),
        "relationship": social.relationship(db, viewer_id, user_id),
    }


# -- analytics ---------------------------------------------------------------


def _number(value: Any) -> float | None:
    text = str(value if value is not None else "").strip().upper().replace(" ", "").replace(",", "")
    if re.fullmatch(r"-?(?:\d+\.?\d*|\.\d+)", text):
        return float(text)
    fraction = re.fullmatch(r"(-?\d+)/(\d+)", text)
    if fraction and int(fraction.group(2)) != 0:
        return int(fraction.group(1)) / int(fraction.group(2))
    return None


def is_correct(question: Mapping[str, Any], answer: Any) -> bool:
    """The frontend's marking, repeated here for stored breakdowns.

    A letter must match; a grid-in matches any accepted spelling, or the same
    number written another way, to the four places the bank rounds to.
    """
    given = str(answer if answer is not None else "").strip().upper()
    if not given:
        return False
    accepted = [question.get("answer"), *(question.get("accepted_answers") or [])]
    accepted = [str(a).strip().upper() for a in accepted if a not in (None, "")]
    if given in accepted:
        return True
    value = _number(given)
    if value is None:
        return False
    return any(other is not None and abs(other - value) < 5e-5 for other in map(_number, accepted))


def analytics(db: Database, user_id: int) -> dict[str, Any]:
    """The rating after every test, and questions right per content domain.

    Both come from what was actually stored: the rating movement recorded with
    each attempt, and the per-question breakdown — the domain of a question
    is on the question itself, so the count is real, not a share of the score.
    """
    rows = db.fetch_all(
        """
        SELECT id, taken_at, section, score, correct, total, test_id, target,
               rating_before, rating_after, details
        FROM attempts WHERE user_id = ? ORDER BY taken_at ASC, id ASC
        """,
        (user_id,),
    )

    points: list[dict[str, Any]] = []
    right: Counter[tuple[str, str]] = Counter()
    seen: Counter[tuple[str, str]] = Counter()
    for row in rows:
        points.append(
            {
                "attempt_id": int(row["id"]),
                "taken_at": row["taken_at"],
                "section": row["section"] or DEFAULT_SECTION,
                "score": row["score"],
                "correct": row["correct"],
                "total": row["total"],
                "rating_before": row["rating_before"],
                "rating_after": row["rating_after"],
            }
        )
        try:
            details = json.loads(row["details"])
        except (json.JSONDecodeError, TypeError):
            details = []
        section = row["section"] or DEFAULT_SECTION
        for entry in details if isinstance(details, list) else []:
            question = entry.get("question") if isinstance(entry, dict) else None
            if not isinstance(question, dict):
                continue
            domain = str(question.get("domain") or "")
            if not domain:
                continue
            seen[(section, domain)] += 1
            if is_correct(question, entry.get("userAnswer")):
                right[(section, domain)] += 1

    topics = []
    for section in SECTIONS:
        for domain in section.domains:
            key = (section.key, domain.name)
            if seen[key]:
                topics.append(
                    {
                        "section": section.key,
                        "domain": domain.name,
                        "correct": right[key],
                        "seen": seen[key],
                    }
                )

    return {"rating_points": points, "topics": topics}


# -- the leaderboard and the platform ----------------------------------------


def leaderboard(db: Database, *, section: str | None = None, limit: int = 20) -> list[dict[str, Any]]:
    """Each student's best attempt in a section: highest score first, quickest on ties."""
    section = section_of(section).key
    limit = max(1, min(MAX_LEADERBOARD, int(limit)))
    rows = db.fetch_all(
        """
        SELECT u.id, u.email, u.username, u.created_at, u.last_login_at, u.is_disabled,
               u.avatar, u.full_name, u.location, u.rating, u.max_rating,
               best.score AS best_score, best.time_spent AS best_time,
               best.taken_at AS best_at, best.correct AS best_correct, best.total AS best_total,
               best.target AS best_target
        FROM (
            SELECT a.*,
                   ROW_NUMBER() OVER (
                       PARTITION BY a.user_id
                       ORDER BY a.score DESC,
                                CASE WHEN a.time_spent > 0 THEN a.time_spent ELSE 999999 END ASC,
                                a.taken_at ASC
                   ) AS place
            FROM attempts a WHERE a.section = ?
        ) best
        JOIN users u ON u.id = best.user_id
        WHERE best.place = 1 AND u.is_disabled = 0
        ORDER BY best.score DESC,
                 CASE WHEN best.time_spent > 0 THEN best.time_spent ELSE 999999 END ASC,
                 best.taken_at ASC
        LIMIT ?
        """,
        (section, limit),
    )
    board = []
    for rank, row in enumerate(rows, start=1):
        board.append(
            {
                "rank": rank,
                "user": accounts.User.from_row(row).public_dict(),
                "score": int(row["best_score"]),
                "time_spent": int(row["best_time"] or 0),
                "taken_at": row["best_at"],
                "correct": int(row["best_correct"]),
                "total": int(row["best_total"]),
                "target": row["best_target"] or "",
            }
        )
    return board


def _country_of(location: str) -> str:
    return " ".join(str(location or "").split(",")[0].split())


def platform_stats(db: Database) -> dict[str, Any]:
    """The platform's real numbers: students, tests, scores, where students are from."""
    students = db.fetch_one("SELECT COUNT(*) AS n FROM users WHERE is_disabled = 0")
    by_section: dict[str, dict[str, Any]] = {}
    for key in SECTION_KEYS:
        row = db.fetch_one(
            """
            SELECT COUNT(*) AS taken, AVG(score) AS average,
                   COUNT(DISTINCT CASE WHEN score = 800 THEN user_id END) AS perfect
            FROM attempts WHERE section = ?
            """,
            (key,),
        )
        by_section[key] = {
            "taken": int(row["taken"] or 0),
            "average": round(float(row["average"])) if row["average"] is not None else None,
            "perfect_scorers": int(row["perfect"] or 0),
        }
    locations = db.fetch_all(
        "SELECT location FROM users WHERE is_disabled = 0 AND location <> ''"
    )
    # "Tajikistan" and "tajikistan" are one country; the first spelling shows.
    countries: Counter[str] = Counter()
    spelling: dict[str, str] = {}
    for row in locations:
        country = _country_of(row["location"])
        if country:
            countries[country.lower()] += 1
            spelling.setdefault(country.lower(), country)
    return {
        "students": int(students["n"] or 0),
        "tests_taken": sum(s["taken"] for s in by_section.values()),
        "by_section": by_section,
        "countries": [
            {"name": spelling[key], "students": count, "flag": COUNTRY_FLAGS.get(key, "🌐")}
            for key, count in countries.most_common(30)
        ],
    }


def tier_of(rating: int | None) -> str:
    return ratings.tier(rating)
