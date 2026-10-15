"""Application settings loaded from environment variables."""

import os


def _timeout_ms():
    raw = os.getenv("MONGO_TIMEOUT_MS", "2500")
    try:
        value = int(raw)
        return value if value > 0 else 2500
    except ValueError:
        return 2500


def get_config():
    """Return Flask config values.

    SECRET_KEY is only used for flash messages/cookies. This app does not
    implement user login. If SECRET_KEY is missing, a random value is used
    for this process so the app can still start locally.
    """
    return {
        "SECRET_KEY": os.getenv("SECRET_KEY") or os.urandom(24),
        "MONGO_URI": os.getenv("MONGO_URI", "mongodb://127.0.0.1:27017/"),
        "MONGO_DB": os.getenv("MONGO_DB", "food_rescue_db"),
        "MONGO_TIMEOUT_MS": _timeout_ms(),
        "SESSION_COOKIE_HTTPONLY": True,
        "SESSION_COOKIE_SAMESITE": "Lax",
        "SESSION_COOKIE_SECURE": os.getenv("SESSION_COOKIE_SECURE", "false").lower() in ("true", "1", "yes"),
    }

