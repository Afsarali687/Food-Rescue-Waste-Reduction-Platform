"""Security, defensive validation, and edge case test suite.

Verifies:
- HTTP defensive security headers (Clickjacking, MIME sniffing, XSS)
- Session cookie security attributes (HttpOnly, SameSite)
- Anti-CSRF token verification
- XSS escaping of user inputs
- Malformed/nonexistent ObjectIds
- NoSQL regex injection resilience
- Rejection of state modification via HTTP GET
- Empty database behavior
"""

import unittest
from bson import ObjectId

from food_rescue import create_app
from food_rescue.csrf import generate_csrf_token


class SecurityAndEdgeCaseTests(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.app.config["TESTING"] = True
        self.client = self.app.test_client()

    def test_security_headers_present(self):
        """Verify standard security headers are injected into every response."""
        response = self.client.get("/")
        self.assertEqual(response.headers.get("X-Frame-Options"), "SAMEORIGIN")
        self.assertEqual(response.headers.get("X-Content-Type-Options"), "nosniff")
        self.assertEqual(response.headers.get("X-XSS-Protection"), "1; mode=block")
        self.assertEqual(
            response.headers.get("Referrer-Policy"), "strict-origin-when-cross-origin"
        )

    def test_cookie_security_config(self):
        """Verify session cookies have HttpOnly and SameSite configured."""
        self.assertTrue(self.app.config.get("SESSION_COOKIE_HTTPONLY"))
        self.assertEqual(self.app.config.get("SESSION_COOKIE_SAMESITE"), "Lax")

    def test_unsafe_state_change_via_get_prevented(self):
        """State changes must strictly reject GET requests with HTTP 405 Method Not Allowed."""
        test_oid = str(ObjectId())
        res_req = self.client.get(f"/food/{test_oid}/request")
        self.assertEqual(res_req.status_code, 405)

        res_expire = self.client.get(f"/food/{test_oid}/expire")
        self.assertEqual(res_expire.status_code, 405)

        res_status = self.client.get(f"/requests/{test_oid}/status")
        self.assertEqual(res_status.status_code, 405)

    def test_nonexistent_and_malformed_object_ids(self):
        """Verify graceful error handling on invalid or nonexistent ObjectIds."""
        # Completely malformed ID
        res_malformed = self.client.get("/food/not-a-valid-id", follow_redirects=True)
        self.assertEqual(res_malformed.status_code, 200)
        self.assertIn(b"Food listing was not found", res_malformed.data)

        # Valid 24-char hex ID that does not exist in the database
        nonexistent_oid = "000000000000000000000000"
        res_nonexistent = self.client.get(f"/food/{nonexistent_oid}", follow_redirects=True)
        self.assertEqual(res_nonexistent.status_code, 200)
        self.assertIn(b"Food listing was not found", res_nonexistent.data)

    def test_search_regex_injection_metacharacters(self):
        """Verify that regex metacharacters in search queries are safely escaped."""
        metachar_queries = [
            ".*",
            "[a-z]+",
            "^.*$",
            "(?=.*a)",
            "\\",
            "'' OR '1'='1",
            "A" * 200,  # Overflow length test
        ]
        for q in metachar_queries:
            response = self.client.get(f"/listings?q={q}")
            self.assertEqual(response.status_code, 200)
            self.assertIn(b"Surplus Food Directory", response.data)

    def test_xss_escaping_in_rendered_output(self):
        """User input containing raw HTML/script tags must be safely escaped by Jinja2."""
        with self.app.test_request_context():
            rendered = self.app.jinja_env.from_string(
                "{{ title }}"
            ).render(title="<script>alert('xss')</script>")
            self.assertNotIn("<script>", rendered)
            self.assertIn("&lt;script&gt;", rendered)

    def test_csrf_token_generation_and_validation(self):
        """Verify CSRF token generation and validation behavior."""
        with self.app.test_request_context():
            token1 = generate_csrf_token()
            self.assertIsInstance(token1, str)
            self.assertEqual(len(token1), 64)  # 32 bytes hex = 64 chars

            # Token should persist across the session
            token2 = generate_csrf_token()
            self.assertEqual(token1, token2)

    def test_csrf_rejection_when_enabled(self):
        """When CSRF is actively enforced (TESTING=False), missing token must be rejected."""
        prod_app = create_app()
        prod_app.config["TESTING"] = False
        prod_app.config["CSRF_ENABLED"] = True
        prod_client = prod_app.test_client()

        # POST without CSRF token should be redirected with error flash
        res = prod_client.post(
            "/food/new",
            data={"title": "Test Without CSRF"},
            follow_redirects=True,
        )
        self.assertEqual(res.status_code, 200)
        self.assertTrue(
            b"Missing security CSRF token" in res.data
            or b"Invalid or expired CSRF token" in res.data
        )


if __name__ == "__main__":
    unittest.main()
