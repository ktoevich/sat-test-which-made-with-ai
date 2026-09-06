from .attempts import bp as attempts_bp
from .auth import bp as auth_bp
from .routes import bp

BLUEPRINTS = (bp, auth_bp, attempts_bp)

__all__ = ["BLUEPRINTS", "bp", "auth_bp", "attempts_bp"]
