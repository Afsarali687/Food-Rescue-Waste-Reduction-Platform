"""Food Rescue & Waste Reduction Platform — Flask application factory."""

from pathlib import Path

from dotenv import load_dotenv
from flask import Flask

from food_rescue.config import get_config
from food_rescue.csrf import init_csrf
from food_rescue.db import init_db
from food_rescue.health import health_bp
from food_rescue.routes import main_bp

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def create_app():
    load_dotenv(PROJECT_ROOT / ".env")

    app = Flask(
        __name__,
        template_folder=str(PROJECT_ROOT / "templates"),
        static_folder=str(PROJECT_ROOT / "static"),
    )
    app.config.from_mapping(get_config())
    app.config["_INDEXES_READY"] = False

    init_db(app)
    init_csrf(app)

    app.register_blueprint(main_bp)
    app.register_blueprint(health_bp)

    @app.after_request
    def set_security_headers(response):
        """Inject modern defensive HTTP security headers into every response."""
        response.headers["X-Frame-Options"] = "SAMEORIGIN"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        return response

    return app
