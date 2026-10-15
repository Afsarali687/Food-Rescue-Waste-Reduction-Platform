"""Unit tests for validation helpers (no MongoDB required)."""

import unittest

from food_rescue.constants import REQUEST_TRANSITIONS
from food_rescue.validation import (
    ValidationError,
    allowed_request_next_statuses,
    can_transition,
    parse_positive_int,
    require_fields,
    validate_category,
    validate_donation_request,
    validate_food_listing,
    validate_request_transition,
)


class ValidationTests(unittest.TestCase):
    def test_require_fields_detects_blanks(self):
        missing = require_fields({"title": "  ", "location": "Hall"}, ("title", "location"))
        self.assertEqual(missing, ["title"])

    def test_parse_positive_int(self):
        self.assertEqual(parse_positive_int("4"), 4)
        with self.assertRaises(ValidationError):
            parse_positive_int("0")
        with self.assertRaises(ValidationError):
            parse_positive_int("abc")

    def test_category_must_be_allowed(self):
        self.assertEqual(validate_category("Bakery"), "Bakery")
        with self.assertRaises(ValidationError):
            validate_category("Pizza")

    def test_food_listing_ok(self):
        data = validate_food_listing(
            {
                "title": "Rice",
                "provider_name": "Canteen",
                "category": "Cooked Meals",
                "quantity": "8",
                "unit": "servings",
                "location": "Gate",
                "expiry_time": "Today, 6 PM",
                "description": "",
                "contact": "",
            }
        )
        self.assertEqual(data["quantity"], 8)
        self.assertEqual(data["pickup_deadline"], "Today, 6 PM")

    def test_food_listing_custom_pickup_deadline(self):
        data = validate_food_listing(
            {
                "title": "Rice",
                "provider_name": "Canteen",
                "category": "Cooked Meals",
                "quantity": "8",
                "unit": "servings",
                "location": "Gate",
                "expiry_time": "Today, 6 PM",
                "pickup_deadline": "Today, 5:30 PM",
                "description": "",
                "contact": "",
            }
        )
        self.assertEqual(data["pickup_deadline"], "Today, 5:30 PM")

    def test_request_quantity_cannot_exceed_available(self):
        with self.assertRaises(ValidationError):
            validate_donation_request(
                {
                    "recipient_name": "A",
                    "organization": "NGO",
                    "contact": "ngo@example.org",
                    "quantity_requested": "5",
                },
                available_quantity=2,
            )

    def test_request_transitions(self):
        self.assertTrue(can_transition("Requested", "Accepted", REQUEST_TRANSITIONS))
        self.assertFalse(can_transition("Requested", "Collected", REQUEST_TRANSITIONS))
        validate_request_transition("Requested", "Accepted")
        with self.assertRaises(ValidationError):
            validate_request_transition("Requested", "Collected")
        self.assertEqual(allowed_request_next_statuses("Collected"), [])


if __name__ == "__main__":
    unittest.main()
