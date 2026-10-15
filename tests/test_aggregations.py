"""Unit tests for MongoDB aggregation pipelines and report metrics."""

from datetime import datetime, timezone
import unittest

from food_rescue import create_app
from food_rescue.aggregations import (
    get_category_breakdown,
    get_donation_activity_by_date,
    get_full_dashboard_reports,
    get_listings_overview,
    get_quantity_by_unit,
    get_request_status_breakdown,
)
from food_rescue.db import (
    donation_records_col,
    donation_requests_col,
    food_listings_col,
    ping_db,
)


class AggregationPipelineTests(unittest.TestCase):
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

    def tearDown(self):
        self.ctx.pop()

    def test_listings_overview_keys_and_types(self):
        if not self.live_db:
            self.skipTest("Live MongoDB not available")

        overview = get_listings_overview()
        self.assertIsInstance(overview, dict)
        expected_keys = [
            "total_listings",
            "available_listings",
            "expired_listings",
            "requested_listings",
            "accepted_listings",
            "collected_listings",
            "total_quantity_listed",
        ]
        for key in expected_keys:
            self.assertIn(key, overview)
            self.assertIsInstance(overview[key], (int, float))

    def test_quantity_by_unit_consistency(self):
        if not self.live_db:
            self.skipTest("Live MongoDB not available")

        unit_breakdown = get_quantity_by_unit()
        self.assertIsInstance(unit_breakdown, list)

        for row in unit_breakdown:
            self.assertIn("unit", row)
            self.assertIn("listed_quantity", row)
            self.assertIn("rescued_quantity", row)
            self.assertIn("rescue_rate", row)
            self.assertTrue(0 <= row["rescue_rate"] <= 100)

    def test_category_breakdown(self):
        if not self.live_db:
            self.skipTest("Live MongoDB not available")

        categories = get_category_breakdown()
        self.assertIsInstance(categories, list)
        for cat in categories:
            self.assertIn("_id", cat)
            self.assertIn("listings_count", cat)
            self.assertIn("total_quantity", cat)

    def test_request_status_breakdown(self):
        if not self.live_db:
            self.skipTest("Live MongoDB not available")

        statuses = get_request_status_breakdown()
        self.assertIsInstance(statuses, list)
        for s in statuses:
            self.assertIn("_id", s)
            self.assertIn("requests_count", s)

    def test_donation_activity_by_date(self):
        if not self.live_db:
            self.skipTest("Live MongoDB not available")

        activity = get_donation_activity_by_date()
        self.assertIsInstance(activity, list)
        for day in activity:
            self.assertIn("_id", day)
            self.assertIn("rescues_count", day)
            self.assertIn("total_quantity_collected", day)

    def test_full_dashboard_reports_structure(self):
        if not self.live_db:
            self.skipTest("Live MongoDB not available")

        report = get_full_dashboard_reports()
        self.assertIn("overview", report)
        self.assertIn("unit_breakdown", report)
        self.assertIn("category_stats", report)
        self.assertIn("request_stats", report)
        self.assertIn("activity_timeline", report)
        self.assertIn("total_requests_count", report)
        self.assertIn("completed_audits_count", report)
        self.assertIn("total_rescued_quantity", report)


if __name__ == "__main__":
    unittest.main()
