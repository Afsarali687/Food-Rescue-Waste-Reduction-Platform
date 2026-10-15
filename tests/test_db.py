"""Tests for database configuration, connection, collections, indexes, and health-check."""

import unittest
from unittest.mock import patch
from pymongo.errors import ServerSelectionTimeoutError

from food_rescue import create_app
from food_rescue.config import get_config
from food_rescue.constants import (
    COLLECTION_USERS,
    COLLECTION_FOOD_LISTINGS,
    COLLECTION_DONATION_REQUESTS,
    COLLECTION_DONATION_RECORDS,
)
from food_rescue.db import (
    get_db,
    ping_db,
    ensure_indexes,
    users_col,
    food_listings_col,
    donation_requests_col,
    donation_records_col,
)


class DatabaseConfigAndConnectionTests(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.app.config["TESTING"] = True
        self.client = self.app.test_client()

    def test_config_loader(self):
        config = get_config()
        self.assertIn("MONGO_URI", config)
        self.assertIn("MONGO_DB", config)
        self.assertEqual(config["MONGO_DB"], "food_rescue_db")
        self.assertIn("MONGO_TIMEOUT_MS", config)
        self.assertIn("SECRET_KEY", config)

    def test_collection_accessors(self):
        with self.app.app_context():
            self.assertEqual(users_col().name, COLLECTION_USERS)
            self.assertEqual(food_listings_col().name, COLLECTION_FOOD_LISTINGS)
            self.assertEqual(donation_requests_col().name, COLLECTION_DONATION_REQUESTS)
            self.assertEqual(donation_records_col().name, COLLECTION_DONATION_RECORDS)

    def test_live_ping_and_indexes(self):
        with self.app.app_context():
            try:
                ping_db()
                live = True
            except Exception:
                live = False

            if live:
                ensure_indexes()
                db = get_db()

                # Verify indexes exist
                user_indexes = [idx["name"] for idx in db[COLLECTION_USERS].list_indexes()]
                self.assertIn("role_1", user_indexes)
                self.assertIn("organization_1", user_indexes)

                food_indexes = [idx["name"] for idx in db[COLLECTION_FOOD_LISTINGS].list_indexes()]
                self.assertIn("status_1_created_at_-1", food_indexes)
                self.assertIn("category_1", food_indexes)
                self.assertIn("provider_name_1", food_indexes)

                req_indexes = [idx["name"] for idx in db[COLLECTION_DONATION_REQUESTS].list_indexes()]
                self.assertIn("listing_id_1", req_indexes)
                self.assertIn("status_1_created_at_-1", req_indexes)

                rec_indexes = [idx["name"] for idx in db[COLLECTION_DONATION_RECORDS].list_indexes()]
                self.assertIn("listing_id_1", rec_indexes)
                self.assertIn("request_id_1", rec_indexes)

    def test_health_endpoint_response_live(self):
        with self.app.app_context():
            try:
                ping_db()
                live = True
            except Exception:
                live = False

        if live:
            res = self.client.get("/health")
            self.assertEqual(res.status_code, 200)
            data = res.get_json()
            self.assertEqual(data["status"], "ok")
            self.assertEqual(data["mongodb"], "connected")
            self.assertEqual(data["database"], "food_rescue_db")
            self.assertEqual(len(data["collections"]), 4)
            self.assertIn("collection_counts", data)
            self.assertIn(COLLECTION_USERS, data["collection_counts"])
            self.assertIn(COLLECTION_FOOD_LISTINGS, data["collection_counts"])

    @patch("food_rescue.health.ping_db")
    def test_health_endpoint_when_db_down(self, mock_ping):
        mock_ping.side_effect = ServerSelectionTimeoutError("Server unreachable")
        res = self.client.get("/health")
        self.assertEqual(res.status_code, 503)
        data = res.get_json()
        self.assertEqual(data["status"], "error")
        self.assertEqual(data["mongodb"], "disconnected")
        self.assertIn("Could not connect to MongoDB", data["message"])


if __name__ == "__main__":
    unittest.main()
