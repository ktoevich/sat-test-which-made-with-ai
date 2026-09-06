"""Admin commands for accounts: look them up, reset, disable, delete.

Passwords are stored as one-way hashes and cannot be shown. When someone
forgets theirs, ``reset-password`` issues a new one; when someone forgets which
address they signed up with, ``list --search`` finds it.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .db import Database, connect
from .security import temporary_password
from .services import accounts, attempts


def _open(target: str | Path) -> Database:
    database = connect(target)
    database.init_schema()
    return database


def _require_user(db: Database, email: str) -> accounts.User:
    user = accounts.find_by_email(db, email)
    if user is None:
        raise SystemExit(f"no account for {email!r}; try: users list --search {email}")
    return user


def cmd_list(args: argparse.Namespace) -> int:
    db = _open(args.database)
    rows = accounts.list_users(db, search=args.search, limit=args.limit)

    if not rows:
        print("no accounts found" if args.search else "no accounts yet")
        return 0

    print(f"{'id':>4}  {'email':<34} {'username':<16} {'attempts':>8} {'best':>5}  registered")
    for row in rows:
        flag = " [disabled]" if row["is_disabled"] else ""
        best = row["best_score"] if row["best_score"] is not None else "-"
        print(
            f"{row['id']:>4}  {row['email']:<34} {row['username']:<16} "
            f"{row['attempts']:>8} {str(best):>5}  {row['created_at'][:10]}{flag}"
        )
    print(f"\n{len(rows)} account(s)")
    return 0


def cmd_show(args: argparse.Namespace) -> int:
    db = _open(args.database)
    user = _require_user(db, args.email)
    history = attempts.list_for_user(db, user.id)
    summary = attempts.summary(db, user.id)

    print(f"id            {user.id}")
    print(f"email         {user.email}")
    print(f"username      {user.username}")
    print(f"registered    {user.created_at}")
    print(f"last login    {user.last_login_at or 'never'}")
    print(f"status        {'disabled' if user.is_disabled else 'active'}")
    print(f"password      stored as a one-way hash; use reset-password to issue a new one")
    print(f"\nattempts      {summary['taken']} | best {summary['best'] or '-'} | avg {summary['average'] or '-'}")

    for attempt in history[: args.limit]:
        print(
            f"  {attempt['taken_at'][:16].replace('T', ' ')}  "
            f"score {attempt['score']:>3}  {attempt['correct']}/{attempt['total']}"
        )
    return 0


def cmd_reset_password(args: argparse.Namespace) -> int:
    db = _open(args.database)
    user = _require_user(db, args.email)

    password = args.password or temporary_password()
    try:
        accounts.set_password(db, user.id, password, iterations=args.iterations)
    except accounts.ValidationFailed as error:
        raise SystemExit(str(error)) from error

    print(f"password reset for {user.email}")
    print(f"temporary password: {password}")
    print("Existing sessions were signed out. Share this over a channel you trust.")
    return 0


def cmd_disable(args: argparse.Namespace) -> int:
    db = _open(args.database)
    user = _require_user(db, args.email)
    accounts.set_disabled(db, user.id, not args.enable)
    print(f"{user.email} is now {'active' if args.enable else 'disabled'}")
    return 0


def cmd_delete(args: argparse.Namespace) -> int:
    db = _open(args.database)
    user = _require_user(db, args.email)
    summary = attempts.summary(db, user.id)

    if not args.yes:
        print(
            f"About to permanently delete {user.email} "
            f"({user.username}) and {summary['taken']} attempt(s).",
            file=sys.stderr,
        )
        raise SystemExit("pass --yes to confirm")

    accounts.delete_user(db, user.id)
    print(f"deleted {user.email} and {summary['taken']} attempt(s)")
    return 0


def register(subparsers, default_database: str | Path, default_iterations: int) -> None:
    """Attach the ``users`` command group to the main parser."""
    users = subparsers.add_parser("users", help="inspect and manage accounts")
    users.add_argument(
        "--database",
        default=str(default_database),
        help="SQLite file path, or a postgres:// URL",
    )
    actions = users.add_subparsers(dest="action", required=True)

    listing = actions.add_parser("list", help="list accounts, newest first")
    listing.add_argument("--search", help="match part of an email or username")
    listing.add_argument("--limit", type=int, default=100)
    listing.set_defaults(func=cmd_list)

    show = actions.add_parser("show", help="one account and its test history")
    show.add_argument("email")
    show.add_argument("--limit", type=int, default=10, help="how many attempts to print")
    show.set_defaults(func=cmd_show)

    reset = actions.add_parser("reset-password", help="issue a new password")
    reset.add_argument("email")
    reset.add_argument("--password", help="set this instead of a generated one")
    reset.add_argument("--iterations", type=int, default=default_iterations)
    reset.set_defaults(func=cmd_reset_password)

    disable = actions.add_parser("disable", help="block sign-in for an account")
    disable.add_argument("email")
    disable.set_defaults(func=cmd_disable, enable=False)

    enable = actions.add_parser("enable", help="unblock an account")
    enable.add_argument("email")
    enable.set_defaults(func=cmd_disable, enable=True)

    delete = actions.add_parser("delete", help="permanently remove an account")
    delete.add_argument("email")
    delete.add_argument("--yes", action="store_true", help="confirm the deletion")
    delete.set_defaults(func=cmd_delete)
