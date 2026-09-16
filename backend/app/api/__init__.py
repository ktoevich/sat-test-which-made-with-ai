from .attempts import bp as attempts_bp
from .auth import bp as auth_bp
from .community import bp as community_bp
from .practice import bp as practice_bp
from .routes import bp
from .social import bp as social_bp

BLUEPRINTS = (bp, auth_bp, attempts_bp, community_bp, social_bp, practice_bp)

__all__ = ["BLUEPRINTS", "bp", "auth_bp", "attempts_bp", "community_bp", "social_bp", "practice_bp"]
