"""The ``bank`` admin commands: put the question bank in the database.

A serverless deployment builds its filesystem from the repository, so a bank
that is deliberately not committed — one built from a third-party export, say —
never reaches it. Pushing the bank into the database the app already uses for
accounts solves that without giving up push-to-deploy.

    python -m app.cli bank push                       # from the default bank file
    python -m app.cli bank push --bank other.json
    python -m app.cli bank status
    python -m app.cli bank pull -o backup.json
    python -m app.cli bank clear
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .bank import assert_valid, summarise
from .db import connect
from .services import bank_store


def _open(args: argparse.Namespace):
    try:
        database = connect(args.database)
    except Exception as error:
        raise SystemExit(f"could not reach the database: {error}") from error
    database.init_schema()
    return database


def _read_bank(path: Path) -> list[dict]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as error:
        raise SystemExit(f"no bank file at {path}") from error
    except json.JSONDecodeError as error:
        raise SystemExit(f"{path} is not valid JSON: {error}") from error
    if not isinstance(data, list):
        raise SystemExit(f"{path} must contain a list of bundles")
    return data


def cmd_push(args: argparse.Namespace) -> int:
    bank = _read_bank(args.bank)
    # The same check `generate` and `import` run before writing a file: a bank
    # that would not be accepted on disk must not reach the database either.
    assert_valid(bank)

    database = _open(args)
    try:
        written = bank_store.replace_all(database, bank)
    finally:
        database.close()

    totals = summarise(bank)
    print(f"pushed {written} test(s), {totals['questions']} questions from {args.bank}")
    print(f"  type        {totals['by_type']}")
    print(f"  difficulty  {totals['by_difficulty']}")
    print("The app now serves these instead of the bank file.")
    return 0


def cmd_status(args: argparse.Namespace) -> int:
    database = _open(args)
    try:
        total = bank_store.count(database)
        stamp = bank_store.updated_at(database)
        ids = bank_store.test_ids(database)
    finally:
        database.close()

    if not total:
        print("the database holds no bank; the app falls back to the bank file")
        return 0

    print(f"{total} test(s) in the database, last pushed {stamp}")
    for test_id in ids:
        print(f"  {test_id}")
    return 0


def cmd_pull(args: argparse.Namespace) -> int:
    database = _open(args)
    try:
        bank = bank_store.fetch_all(database)
    finally:
        database.close()

    if not bank:
        raise SystemExit("the database holds no bank")
    if args.output.exists() and not args.force:
        raise SystemExit(f"{args.output} exists; pass --force to overwrite")

    args.output.write_text(json.dumps(bank, indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"wrote {len(bank)} test(s) -> {args.output}")
    return 0


def cmd_clear(args: argparse.Namespace) -> int:
    database = _open(args)
    try:
        total = bank_store.count(database)
        if not total:
            print("the database holds no bank; nothing to clear")
            return 0
        if not args.yes:
            print(
                f"this removes {total} test(s) from the database and the app falls back "
                "to the bank file; pass --yes to go ahead",
                file=sys.stderr,
            )
            return 1
        bank_store.clear(database)
    finally:
        database.close()

    print(f"removed {total} test(s); the app falls back to the bank file")
    return 0


def register(subparsers, default_database: str | Path, default_bank: Path) -> None:
    """Attach the ``bank`` command group to the main parser."""
    bank = subparsers.add_parser("bank", help="keep the question bank in the database")
    bank.add_argument(
        "--database",
        default=str(default_database),
        help="SQLite file path, or a postgres:// URL",
    )
    actions = bank.add_subparsers(dest="action", required=True)

    push = actions.add_parser("push", help="replace the stored bank with a bank file")
    push.add_argument("--bank", type=Path, default=default_bank)
    push.set_defaults(func=cmd_push)

    status = actions.add_parser("status", help="what the database currently holds")
    status.set_defaults(func=cmd_status)

    pull = actions.add_parser("pull", help="write the stored bank back out to a file")
    pull.add_argument("-o", "--output", type=Path, default=Path("bank-from-database.json"))
    pull.add_argument("--force", action="store_true", help="overwrite an existing file")
    pull.set_defaults(func=cmd_pull)

    clear = actions.add_parser("clear", help="empty the stored bank")
    clear.add_argument("--yes", action="store_true", help="confirm the removal")
    clear.set_defaults(func=cmd_clear)
