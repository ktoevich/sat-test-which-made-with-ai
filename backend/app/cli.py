"""Command line tools for the question bank.

    python -m app.cli validate [--bank PATH]
    python -m app.cli stats    [--bank PATH]
    python -m app.cli generate --bundles 3 -o data/tests_bundle_cache.json
    python -m app.cli import export.csv --bundles 2 -o data/tests_bundle_cache.json
    python -m app.cli users list
    python -m app.cli users reset-password student@example.com

Run from the ``backend/`` directory.
"""

from __future__ import annotations

import argparse
import json
import random
import sys
from pathlib import Path
from typing import Any, Sequence

from .bank import (
    AssemblyError,
    BankValidationError,
    GenerationError,
    assemble_bank,
    assert_valid,
    default_spec,
    generate_bank,
    import_questions,
    load_source,
    summarise,
    validate_bank,
)
from .bank.importer import ImportError_
from .config import BaseConfig
from . import cli_users

DEFAULT_BANK = BaseConfig.QUESTION_BANK_PATH
DEFAULT_DATABASE = BaseConfig.DATABASE_URL or BaseConfig.DATABASE_PATH


def _read_bank(path: Path) -> Any:
    if not path.is_file():
        raise SystemExit(f"bank file not found: {path}")
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise SystemExit(f"{path} is not valid JSON: {error}") from error


def _write_bank(bundles: list[dict], path: Path, *, force: bool) -> None:
    if path.exists() and not force:
        raise SystemExit(f"{path} already exists; pass --force to overwrite it")

    assert_valid(bundles)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(bundles, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    counts = summarise(bundles)
    print(f"wrote {counts['bundles']} bundle(s), {counts['questions']} questions -> {path}")
    _print_counts(counts)


def _print_counts(counts: dict[str, Any]) -> None:
    for label in ("by_type", "by_difficulty", "by_domain"):
        parts = ", ".join(f"{key}: {value}" for key, value in sorted(counts[label].items()))
        print(f"  {label.removeprefix('by_'):<11} {parts}")


# -- commands ----------------------------------------------------------


def cmd_validate(args: argparse.Namespace) -> int:
    issues = validate_bank(_read_bank(args.bank))
    if not issues:
        print(f"{args.bank}: valid")
        return 0

    print(f"{args.bank}: {len(issues)} problem(s)", file=sys.stderr)
    for issue in issues[: args.limit]:
        print(f"  {issue}", file=sys.stderr)
    if len(issues) > args.limit:
        print(f"  ... and {len(issues) - args.limit} more", file=sys.stderr)
    return 1


def cmd_stats(args: argparse.Namespace) -> int:
    counts = summarise(_read_bank(args.bank))
    print(f"{args.bank}: {counts['bundles']} bundle(s), {counts['questions']} questions")
    parts = ", ".join(f"{key}: {value}" for key, value in sorted(counts["by_module"].items()))
    print(f"  {'module':<11} {parts}")
    _print_counts(counts)
    return 0


def cmd_generate(args: argparse.Namespace) -> int:
    rng = random.Random(args.seed)
    spec = default_spec(size=args.module_size, spr_count=args.spr)
    try:
        bundles = generate_bank(
            bundles=args.bundles, spec=spec, rng=rng, test_id_prefix=args.prefix
        )
    except (GenerationError, AssemblyError) as error:
        raise SystemExit(str(error)) from error

    _write_bank(bundles, args.output, force=args.force)
    return 0


def cmd_import(args: argparse.Namespace) -> int:
    try:
        rows = load_source(args.source)
        questions, problems = import_questions(rows, skip_invalid=args.skip_invalid)
    except ImportError_ as error:
        raise SystemExit(str(error)) from error

    for problem in problems:
        print(f"skipped: {problem}", file=sys.stderr)
    print(f"read {len(questions)} question(s) from {args.source}")

    spec = default_spec(size=args.module_size, spr_count=args.spr)
    try:
        bundles = assemble_bank(
            questions,
            bundles=args.bundles,
            spec=spec,
            rng=random.Random(args.seed),
            test_id_prefix=args.prefix,
        )
    except AssemblyError as error:
        raise SystemExit(str(error)) from error

    _write_bank(bundles, args.output, force=args.force)
    return 0


# -- parser ------------------------------------------------------------


def _add_build_arguments(parser: argparse.ArgumentParser, prefix: str) -> None:
    parser.add_argument("-o", "--output", type=Path, default=DEFAULT_BANK, help="where to write the bank")
    parser.add_argument("--bundles", type=int, default=1, help="how many tests to build")
    parser.add_argument("--module-size", type=int, default=22, help="questions per module")
    parser.add_argument("--spr", type=int, default=6, help="grid-in questions per module")
    parser.add_argument("--seed", type=int, default=None, help="seed for reproducible output")
    parser.add_argument("--prefix", default=prefix, help="prefix for generated test ids")
    parser.add_argument("--force", action="store_true", help="overwrite an existing output file")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="app.cli", description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)

    validate = sub.add_parser("validate", help="check a bank file against the schema")
    validate.add_argument("--bank", type=Path, default=DEFAULT_BANK)
    validate.add_argument("--limit", type=int, default=25, help="max problems to print")
    validate.set_defaults(func=cmd_validate)

    stats = sub.add_parser("stats", help="summarise a bank file")
    stats.add_argument("--bank", type=Path, default=DEFAULT_BANK)
    stats.set_defaults(func=cmd_stats)

    generate = sub.add_parser("generate", help="build original questions from the templates")
    _add_build_arguments(generate, "sat-generated")
    generate.set_defaults(func=cmd_generate)

    importer = sub.add_parser("import", help="normalise a question export you already have")
    importer.add_argument("source", type=Path, help="path to a .json or .csv export")
    importer.add_argument(
        "--skip-invalid", action="store_true", help="drop unusable rows instead of failing"
    )
    _add_build_arguments(importer, "sat-imported")
    importer.set_defaults(func=cmd_import)

    cli_users.register(sub, DEFAULT_DATABASE, BaseConfig.PASSWORD_ITERATIONS)

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return args.func(args)
    except BankValidationError as error:
        print("the result did not pass validation:", file=sys.stderr)
        for issue in error.issues[:25]:
            print(f"  {issue}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
