"""Lightweight, dependency-free Cross-Site Request Forgery (CSRF) protection.

This module provides anti-CSRF token generation and verification using Python's
cryptographically secure `secrets` library and constant-time string comparison.
"""

import secrets
from flask import current_app, flash, redirect, request, session


class CSRFError(Exception):
    """Raised when a CSRF token is invalid or missing."""


def generate_csrf_token():
    """Generate or retrieve a cryptographically secure CSRF token for the current session."""
    if "_csrf_token" not in session:
        session["_csrf_token"] = secrets.token_hex(32)
    return session["_csrf_token"]


def validate_csrf():
    """Verify the submitted CSRF token on POST/PUT/DELETE requests.

    Skips validation if:
    - The request method is safe (GET, HEAD, OPTIONS).
    - The application is running in TESTING mode.
    """
    if request.method in ("GET", "HEAD", "OPTIONS"):
        return

    # Allow test runners to bypass CSRF validation
    if current_app.config.get("TESTING") or not current_app.config.get("CSRF_ENABLED", True):
        return

    session_token = session.get("_csrf_token")
    submitted_token = request.form.get("csrf_token") or request.headers.get("X-CSRF-Token")

    if not session_token or not submitted_token:
        raise CSRFError("Missing security CSRF token. Please refresh the page and try again.")

    if not secrets.compare_digest(session_token, submitted_token):
        raise CSRFError("Invalid or expired CSRF token. Submission rejected for security.")


def init_csrf(app):
    """Register CSRF template helper, validation hook, and error handling on the Flask app."""
    app.jinja_env.globals["csrf_token"] = generate_csrf_token

    @app.before_request
    def _csrf_protect():
        try:
            validate_csrf()
        except CSRFError as exc:
            flash(str(exc), "error")
            return redirect(request.referrer or "/")
