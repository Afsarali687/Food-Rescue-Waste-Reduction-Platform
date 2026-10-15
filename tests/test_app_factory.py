"""Import and HTTP tests for the Flask application factory and primary views."""

import unittest

from food_rescue import create_app


class AppFactoryTests(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.app.config["TESTING"] = True
        self.client = self.app.test_client()

    def test_create_app_imports(self):
        self.assertIsNotNone(self.app)

    def test_health_endpoint_exists(self):
        response = self.client.get("/health")
        self.assertIn(response.status_code, (200, 503))
        payload = response.get_json()
        self.assertIn("status", payload)
        self.assertIn("mongodb", payload)
        self.assertIn("collections", payload)
        self.assertEqual(len(payload["collections"]), 4)

    def test_home_page_renders_without_crash(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Rescuing Surplus Food", response.data)

    def test_listings_page_renders_without_crash(self):
        response = self.client.get("/listings")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Surplus Food Directory", response.data)

    def test_listings_page_filtering(self):
        response = self.client.get("/listings?q=Bread&category=Bakery&status=all")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Surplus Food Directory", response.data)

    def test_create_food_page_renders(self):
        response = self.client.get("/food/new")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"List Surplus Food", response.data)

    def test_manage_requests_page_renders(self):
        response = self.client.get("/requests")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Donation Requests", response.data)

    def test_reports_page_renders(self):
        response = self.client.get("/reports")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Impact & Waste Diversion Analytics", response.data)


if __name__ == "__main__":
    unittest.main()
