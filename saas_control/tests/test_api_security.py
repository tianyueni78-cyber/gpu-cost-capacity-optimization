import unittest

from fastapi.testclient import TestClient

from saas_control.app.main import create_app


class ApiSecurityTest(unittest.TestCase):
    def setUp(self):
        def decode(token):
            if token != "valid-token":
                raise ValueError("invalid")
            return {"sub": "USER-1", "organization_id": "ORG-1", "project_id": "PROJECT-1", "role": "ANALYST", "subscription_active": True}

        self.client = TestClient(create_app(decode))

    def test_health_check_is_public_and_has_request_id(self):
        response = self.client.get("/healthz")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok"})
        self.assertTrue(response.headers["x-request-id"])

    def test_missing_or_invalid_token_is_unauthorized(self):
        self.assertEqual(self.client.get("/v1/context").status_code, 401)
        self.assertEqual(self.client.get("/v1/context", headers={"Authorization": "Bearer bad"}).status_code, 401)

    def test_identity_comes_from_token_not_owner_query(self):
        response = self.client.get("/v1/context?owner_id=OTHER", headers={"Authorization": "Bearer valid-token"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["user_id"], "USER-1")
        self.assertNotIn("owner_id", response.json())

    def test_cross_project_lookup_is_not_found(self):
        response = self.client.get("/v1/projects/OTHER", headers={"Authorization": "Bearer valid-token"})
        self.assertEqual(response.status_code, 404)


if __name__ == "__main__":
    unittest.main()
