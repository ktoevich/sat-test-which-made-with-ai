"""Vercel entrypoint.

Vercel looks for a Flask instance named ``app`` at a supported entrypoint in the
repository root. The application itself lives in ``backend/app``; this module
only puts that directory on the import path and builds the app.
"""

from __future__ import annotations

import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app import create_app  # noqa: E402  (import needs the path set above)

app = create_app("production")
