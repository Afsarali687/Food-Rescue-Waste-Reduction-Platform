"""Unit and integration tests for the donation request workflow and lifecycle transitions."""

from datetime import datetime, timezone
import unittest
from bson import ObjectId

from food_rescue import create_app
from food_rescue.constants import (
    COLLECTION_DONATION_RECORDS,
    COLLECTION_DONATION_REQUESTS,
    COLLECTION_FOOD_LISTINGS,
    COLLECTION_USERS,
)
from food_rescue.db import (
    donation_records_col,
    donation_requests_col,
    food_listings_col,
    get_db,
    ping_db,
    users_col,
)
from food_rescue.validation import ValidationError
from food_rescue.workflow import (
    mark_listing_expired,
    submit_donation_request,
    transition_request_status,
)


class WorkflowTests(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.app.config["TESTING"] = True
        self.ctx = self.app.app_context()
        self.ctx.push()

        try:
            ping_db()
            self.live_db = True
        except Exception:
            self.live_db = False

        if self.live_db:
            # Create a test listing
            self.now = datetime.now(timezone.utc)
            self.test_listing_id = food_listings_col().insert_one(
                {
                    "title": "Workflow Test Meals",
                    "provider_name": "Test Dining Hall",
                    "category": "Cooked Meals",
                    "quantity": 10,
                    "unit": "servings",
                    "location": "North Campus",
                    "expiry_time": "Today, 9:00 PM",
                    "pickup_deadline": "Today, 8:30 PM",
                    "status": "Available",
                    "created_at": self.now,
                    "updated_at": self.now,
                }
            ).inserted_id

            # Create an authorized recipient user
            self.recipient_user_id = users_col().insert_one(
                {
                    "name": "Sarah Jenkins",
                    "role": "recipient",
                    "organization": "Community Shelter",
                    "contact": "sarah@shelter.org",
                    "created_at": self.now,
                }
            ).inserted_id

            # Create an unauthorized provider user
            self.provider_user_id = users_col().insert_one(
                {
                    "name": "Dining Manager",
                    "role": "provider",
                    "organization": "Test Dining Hall",
                    "contact": "dining@campus.edu",
                    "created_at": self.now,
                }
            ).inserted_id

    def tearDown(self):
        if self.live_db:
            # Clean up test documents
            if hasattr(self, "test_listing_id"):
                food_listings_col().delete_one({"_id": self.test_listing_id})
                donation_requests_col().delete_many({"listing_id": self.test_listing_id})
                donation_records_col().delete_many({"listing_id": self.test_listing_id})
            if hasattr(self, "recipient_user_id"):
                users_col().delete_one({"_id": self.recipient_user_id})
            if hasattr(self, "provider_user_id"):
                users_col().delete_one({"_id": self.provider_user_id})
        self.ctx.pop()

    def test_submit_donation_request_success(self):
        if not self.live_db:
            self.skipTest("Live MongoDB not available")

        req = submit_donation_request(
            str(self.test_listing_id),
            {
                "recipient_name": "Sarah Jenkins",
                "organization": "Community Shelter",
                "contact": "sarah@shelter.org",
                "quantity_requested": "4",
            },
            recipient_user_id=str(self.recipient_user_id),
        )

        self.assertIsNotNone(req)
        self.assertEqual(req["status"], "Requested")
        self.assertEqual(req["quantity_requested"], 4)

        # Verify listing was moved to Requested
        listing = food_listings_col().find_one({"_id": self.test_listing_id})
        self.assertEqual(listing["status"], "Requested")

    def test_request_quantity_exceeding_available_is_rejected(self):
        if not self.live_db:
            self.skipTest("Live MongoDB not available")

        with self.assertRaises(ValidationError) as ctx:
            submit_donation_request(
                str(self.test_listing_id),
                {
                    "recipient_name": "Sarah Jenkins",
                    "organization": "Community Shelter",
                    "contact": "sarah@shelter.org",
                    "quantity_requested": "15",  # Available is 10
                },
            )
        self.assertIn("exceed", str(ctx.exception).lower())

    def test_duplicate_active_request_prevented(self):
        if not self.live_db:
            self.skipTest("Live MongoDB not available")

        # First request succeeds
        submit_donation_request(
            str(self.test_listing_id),
            {
                "recipient_name": "Sarah Jenkins",
                "organization": "Community Shelter",
                "contact": "sarah@shelter.org",
                "quantity_requested": "2",
            },
        )

        # Second request must be rejected
        with self.assertRaises(ValidationError) as ctx:
            submit_donation_request(
                str(self.test_listing_id),
                {
                    "recipient_name": "Another NGO",
                    "organization": "Shelter Two",
                    "contact": "two@shelter.org",
                    "quantity_requested": "2",
                },
            )
        self.assertTrue(
            "active donation request" in str(ctx.exception).lower()
            or "not available" in str(ctx.exception).lower()
        )

    def test_requesting_expired_listing_is_rejected(self):
        if not self.live_db:
            self.skipTest("Live MongoDB not available")

        # Mark listing expired
        food_listings_col().update_one(
            {"_id": self.test_listing_id}, {"$set": {"status": "Expired"}}
        )

        with self.assertRaises(ValidationError) as ctx:
            submit_donation_request(
                str(self.test_listing_id),
                {
                    "recipient_name": "Sarah Jenkins",
                    "organization": "Community Shelter",
                    "contact": "sarah@shelter.org",
                    "quantity_requested": "2",
                },
            )
        self.assertIn("expired", str(ctx.exception).lower())

    def test_claimant_role_authorization_check(self):
        if not self.live_db:
            self.skipTest("Live MongoDB not available")

        # Provider user trying to claim food must be rejected
        with self.assertRaises(ValidationError) as ctx:
            submit_donation_request(
                str(self.test_listing_id),
                {
                    "recipient_name": "Dining Manager",
                    "organization": "Campus Dining",
                    "contact": "dining@campus.edu",
                    "quantity_requested": "2",
                },
                recipient_user_id=str(self.provider_user_id),
            )
        self.assertIn("authorized", str(ctx.exception).lower())

    def test_full_lifecycle_requested_to_accepted_to_collected(self):
        if not self.live_db:
            self.skipTest("Live MongoDB not available")

        # 1. Submit Request
        req = submit_donation_request(
            str(self.test_listing_id),
            {
                "recipient_name": "Sarah Jenkins",
                "organization": "Community Shelter",
                "contact": "sarah@shelter.org",
                "quantity_requested": "5",
            },
        )
        req_id = str(req["_id"])

        # 2. Accept Request (by provider)
        updated_req, listing_status = transition_request_status(
            req_id, "Accepted", actor_role="provider"
        )
        self.assertEqual(updated_req["status"], "Accepted")
        self.assertEqual(listing_status, "Accepted")

        # Verify listing status in DB
        listing = food_listings_col().find_one({"_id": self.test_listing_id})
        self.assertEqual(listing["status"], "Accepted")

        # 3. Mark Collected (hand-off)
        updated_req, listing_status = transition_request_status(
            req_id, "Collected", actor_role="provider"
        )
        self.assertEqual(updated_req["status"], "Collected")
        self.assertEqual(listing_status, "Collected")

        # Verify permanent record in donation_records
        record = donation_records_col().find_one({"request_id": req["_id"]})
        self.assertIsNotNone(record)
        self.assertEqual(record["quantity_collected"], 5)
        self.assertEqual(record["recipient_name"], "Sarah Jenkins")
        self.assertEqual(record["unit"], "servings")

    def test_cancel_reverts_listing_to_available(self):
        if not self.live_db:
            self.skipTest("Live MongoDB not available")

        # 1. Submit Request -> Listing becomes Requested
        req = submit_donation_request(
            str(self.test_listing_id),
            {
                "recipient_name": "Sarah Jenkins",
                "organization": "Community Shelter",
                "contact": "sarah@shelter.org",
                "quantity_requested": "5",
            },
        )
        req_id = str(req["_id"])

        # 2. Cancel Request -> Listing must revert to Available
        updated_req, listing_status = transition_request_status(req_id, "Cancelled")
        self.assertEqual(updated_req["status"], "Cancelled")
        self.assertEqual(listing_status, "Available")

        listing = food_listings_col().find_one({"_id": self.test_listing_id})
        self.assertEqual(listing["status"], "Available")

    def test_invalid_status_transition_rejected(self):
        if not self.live_db:
            self.skipTest("Live MongoDB not available")

        # 1. Submit Request
        req = submit_donation_request(
            str(self.test_listing_id),
            {
                "recipient_name": "Sarah Jenkins",
                "organization": "Community Shelter",
                "contact": "sarah@shelter.org",
                "quantity_requested": "5",
            },
        )
        req_id = str(req["_id"])

        # Trying to jump directly from Requested to Collected must be rejected
        with self.assertRaises(ValidationError):
            transition_request_status(req_id, "Collected")

    def test_mark_listing_expired(self):
        if not self.live_db:
            self.skipTest("Live MongoDB not available")

        updated = mark_listing_expired(str(self.test_listing_id))
        self.assertEqual(updated["status"], "Expired")

        listing = food_listings_col().find_one({"_id": self.test_listing_id})
        self.assertEqual(listing["status"], "Expired")


if __name__ == "__main__":
    unittest.main()
