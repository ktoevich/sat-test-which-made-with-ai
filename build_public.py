"""Copy the static frontend into ./public for the CDN to serve.

Vercel serves everything under ``public/`` straight from the CDN and sends the
remaining requests to the Python function, so the browser gets the HTML, CSS and
JS without waking a function at all.
"""

from __future__ import annotations

import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / "frontend"
TARGET = ROOT / "public"

#: Development-only files that must not be published.
EXCLUDE = shutil.ignore_patterns(
    "tests", "node_modules", "package.json", "package-lock.json", ".*"
)


def main() -> None:
    if not SOURCE.is_dir():
        raise SystemExit(f"frontend directory not found: {SOURCE}")

    if TARGET.exists():
        shutil.rmtree(TARGET)
    shutil.copytree(SOURCE, TARGET, ignore=EXCLUDE)

    files = sorted(path for path in TARGET.rglob("*") if path.is_file())
    print(f"copied {len(files)} file(s) into {TARGET.relative_to(ROOT)}/")
    for path in files:
        print(f"  {path.relative_to(TARGET)}")


if __name__ == "__main__":
    main()
