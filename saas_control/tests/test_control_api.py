import unittest

from fastapi.testclient import TestClient

from saas_control.app.main import create_app


class FakeStore:
    def __init__(self):
        self.jobs = {}

    def authenticate(self, user_id, password):
        if (user_id, password) != ("USER-A", "local-only"):
            return None
        return [{"organization_id": "ORG-A", "organization_name": "Student Lab", "project_id": "PROJECT-A", "project_name": "GPU Pilot"}]

    def has_access(self, user_id, organization_id, project_id):
        return user_id == "USER-A" and (organization_id, project_id) == ("ORG-A", "PROJECT-A")

    def products(self, organization_id):
        return ["gpu-data", "gpu-optimize", "gpu-improve", "gpu-forecast"]

    def submit_job(self, tenant, product, operation, key):
        identity = (tenant.organization_id, key)
        if identity not in self.jobs:
            self.jobs[identity] = {
                "job_id": f"JOB-{len(self.jobs)+1}",
                "organization_id": tenant.organization_id,
                "project_id": tenant.project_id,
                "product": product.value,
                "operation": operation,
                "idempotency_key": key,
                "status": "QUEUED",
            }
        return self.jobs[identity]

    def list_jobs(self, tenant):
        return [job for job in self.jobs.values() if job["organization_id"] == tenant.organization_id and job["project_id"] == tenant.project_id]

    def status(self):
        return {"database": "ok", "redis": "ok", "worker": "ok"}


class LocalControlApiTest(unittest.TestCase):
    def setUp(self):
        self.store = FakeStore()
        self.client = TestClient(create_app(
            lambda token: {
                "sub": "USER-A",
                "organization_id": "ORG-A",
                "project_id": "PROJECT-A",
                "role": "ANALYST",
                "subscription_active": True,
            } if token == "selected-token" else ({"sub": "USER-A"} if token == "selection-token" else (_ for _ in ()).throw(ValueError("invalid"))),
            store=self.store,
            issue_token=lambda user, org=None, project=None: "selected-token" if org else "selection-token",
            dev_credentials=("student@example.com", "local-only", "USER-A"),
        ))

    def test_login_selects_tenant_and_lists_four_products(self):
        login = self.client.post("/v1/dev/login", json={"email": "student@example.com", "password": "local-only"})
        self.assertEqual(login.status_code, 200)
        self.assertEqual(login.json()["tenants"][0]["project_id"], "PROJECT-A")
        selection_headers = {"Authorization": f"Bearer {login.json()['selection_token']}"}
        selected = self.client.post("/v1/dev/select", json={"organization_id": "ORG-A", "project_id": "PROJECT-A"}, headers=selection_headers)
        self.assertEqual(selected.json()["access_token"], "selected-token")
        products = self.client.get("/v1/products", headers={"Authorization": "Bearer selected-token"})
        self.assertEqual(len(products.json()["products"]), 4)

    def test_jobs_are_idempotent_and_tenant_scoped(self):
        headers = {"Authorization": "Bearer selected-token"}
        body = {"product": "gpu-data", "operation": "IMPORT", "idempotency_key": "same"}
        first = self.client.post("/v1/jobs", json=body, headers=headers)
        second = self.client.post("/v1/jobs", json=body, headers=headers)
        self.assertEqual(first.status_code, 202)
        self.assertEqual(first.json()["job_id"], second.json()["job_id"])
        self.assertEqual(self.client.get("/v1/jobs", headers=headers).json()["jobs"][0]["organization_id"], "ORG-A")

    def test_wrong_tenant_selection_is_not_found(self):
        login = self.client.post("/v1/dev/login", json={"email": "student@example.com", "password": "local-only"})
        selection_headers = {"Authorization": f"Bearer {login.json()['selection_token']}"}
        response = self.client.post("/v1/dev/select", json={"organization_id": "ORG-B", "project_id": "PROJECT-B"}, headers=selection_headers)
        self.assertEqual(response.status_code, 404)

    def test_configured_email_does_not_have_to_match_seed_email(self):
        client = TestClient(create_app(
            lambda _token: {"sub": "USER-A"},
            store=self.store,
            issue_token=lambda user, org=None, project=None: "selection-token",
            dev_credentials=("me@example.com", "local-only", "USER-A"),
        ))
        response = client.post("/v1/dev/login", json={"email": "me@example.com", "password": "local-only"})
        self.assertEqual(response.status_code, 200)

    def test_viewer_cannot_submit_analysis_job(self):
        client = TestClient(create_app(
            lambda token: {
                "sub": "USER-A",
                "organization_id": "ORG-A",
                "project_id": "PROJECT-A",
                "role": "VIEWER",
                "subscription_active": True,
            },
            store=self.store,
        ))
        response = client.post(
            "/v1/jobs",
            json={"product": "gpu-data", "operation": "IMPORT", "idempotency_key": "viewer"},
            headers={"Authorization": "Bearer viewer-token"},
        )
        self.assertEqual(response.status_code, 403)


if __name__ == "__main__":
    unittest.main()
