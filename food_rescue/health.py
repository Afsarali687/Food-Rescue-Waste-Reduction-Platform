"""Health-check blueprint: confirms the process is up and MongoDB is reachable."""

from flask import Blueprint, current_app, jsonify
from pymongo.errors import PyMongoError

from food_rescue.constants import (
    COLLECTION_DONATION_RECORDS,
    COLLECTION_DONATION_REQUESTS,
    COLLECTION_FOOD_LISTINGS,
    COLLECTION_USERS,
)
from food_rescue.db import db_error_message, get_db, ping_db

health_bp = Blueprint("health", __name__)


@health_bp.route("/health")
def health():
    payload = {
        "status": "ok",
        "service": "food-rescue",
        "database": current_app.config["MONGO_DB"],
        "mongodb": "disconnected",
        "collections": [
            COLLECTION_USERS,
            COLLECTION_FOOD_LISTINGS,
            COLLECTION_DONATION_REQUESTS,
            COLLECTION_DONATION_RECORDS,
        ],
    }
    try:
        ping_db()
        db = get_db()
        payload["mongodb"] = "connected"
        payload["collection_counts"] = {
            COLLECTION_USERS: db[COLLECTION_USERS].estimated_document_count(),
            COLLECTION_FOOD_LISTINGS: db[COLLECTION_FOOD_LISTINGS].estimated_document_count(),
            COLLECTION_DONATION_REQUESTS: db[COLLECTION_DONATION_REQUESTS].estimated_document_count(),
            COLLECTION_DONATION_RECORDS: db[COLLECTION_DONATION_RECORDS].estimated_document_count(),
        }
        return jsonify(payload), 200
    except PyMongoError as exc:
        payload["status"] = "error"
        payload["message"] = db_error_message(exc)
        payload["error_type"] = exc.__class__.__name__
        return jsonify(payload), 503
