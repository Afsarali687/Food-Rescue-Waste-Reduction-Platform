"""MongoDB connection, indexes, and collection helpers."""

from flask import current_app, g
from pymongo import ASCENDING, DESCENDING, MongoClient
from pymongo.errors import ConnectionFailure, PyMongoError, ServerSelectionTimeoutError

from food_rescue.constants import (
    COLLECTION_DONATION_RECORDS,
    COLLECTION_DONATION_REQUESTS,
    COLLECTION_FOOD_LISTINGS,
    COLLECTION_USERS,
)


def get_client():
    if "mongo_client" not in g:
        g.mongo_client = MongoClient(
            current_app.config["MONGO_URI"],
            serverSelectionTimeoutMS=current_app.config["MONGO_TIMEOUT_MS"],
        )
    return g.mongo_client


def get_db():
    if "mongo_db" not in g:
        g.mongo_db = get_client()[current_app.config["MONGO_DB"]]
    return g.mongo_db


def users_col():
    return get_db()[COLLECTION_USERS]


def food_listings_col():
    return get_db()[COLLECTION_FOOD_LISTINGS]


def donation_requests_col():
    return get_db()[COLLECTION_DONATION_REQUESTS]


def donation_records_col():
    return get_db()[COLLECTION_DONATION_RECORDS]


def ping_db():
    get_client().admin.command("ping")


def close_db(_error=None):
    g.pop("mongo_db", None)
    client = g.pop("mongo_client", None)
    if client is not None:
        client.close()


def db_error_message(exc):
    """Student-friendly explanation of a PyMongo failure."""
    if isinstance(exc, (ServerSelectionTimeoutError, ConnectionFailure)):
        return (
            "Could not connect to MongoDB. Start MongoDB Community Server, "
            "or update MONGO_URI in your .env file if you use Atlas."
        )
    return f"A database error occurred ({exc.__class__.__name__}). Check MongoDB and try again."


def ensure_indexes():
    """Create useful indexes. Safe to run more than once."""
    users_col().create_index([("role", ASCENDING)])
    users_col().create_index([("organization", ASCENDING)])

    food_listings_col().create_index([("status", ASCENDING), ("created_at", DESCENDING)])
    food_listings_col().create_index([("category", ASCENDING)])
    food_listings_col().create_index([("provider_name", ASCENDING)])
    food_listings_col().create_index([("location", ASCENDING)])

    donation_requests_col().create_index([("listing_id", ASCENDING)])
    donation_requests_col().create_index([("status", ASCENDING), ("created_at", DESCENDING)])

    donation_records_col().create_index([("listing_id", ASCENDING)])
    donation_records_col().create_index("request_id", unique=True)


def init_db(app):
    app.teardown_appcontext(close_db)

    @app.before_request
    def _ensure_indexes_once():
        if app.config.get("_INDEXES_READY"):
            return
        try:
            ping_db()
            ensure_indexes()
            app.config["_INDEXES_READY"] = True
        except PyMongoError as exc:
            app.logger.warning("MongoDB not ready: %s", exc)
