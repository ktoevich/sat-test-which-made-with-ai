"""WSGI entry point.

Development:  python wsgi.py           (Flask's reloader, debug on)
Production:   gunicorn "wsgi:app"      (see README)
"""

from __future__ import annotations

import os

from app import create_app

app = create_app()

if __name__ == "__main__":
    host = os.environ.get("HOST", "127.0.0.1")
    port = int(os.environ.get("PORT", "5000"))
    print(f"SAT practice API running on http://{host}:{port}")
    app.run(host=host, port=port, debug=app.config["DEBUG"])
