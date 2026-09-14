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

    def create_sample_dataset(self, tenant, _sample_root):
        return {"dataset_id": "DATASET-1", "source_type": "SAMPLE", "status": "READY", "row_counts": {"inventory": 2}}

    def create_public_dataset(self, tenant, _source_root):
        return {"dataset_id": "DATASET-PUBLIC", "source_type": "PUBLIC", "status": "READY", "row_counts": {"inventory": 8}}

    def create_dataset(self, tenant, files, source_type):
        return {"dataset_id": "DATASET-UPLOAD", "source_type": source_type, "status": "READY", "files": list(files)}

    def get_dataset(self, tenant, dataset_id):
        return {"dataset_id": dataset_id, "status": "READY"} if dataset_id == "DATASET-1" else None

    def submit_gpu_data_analysis(self, tenant, dataset_id, key):
        if dataset_id != "DATASET-1":
            return None
        return {"job_id": "GPU-DATA-JOB", "dataset_id": dataset_id, "idempotency_key": key, "status": "QUEUED"}

    def get_analysis(self, tenant, dataset_id):
        return {"dataset_id": dataset_id, "status": "SUCCEEDED", "summary": {"total_cost_usd": 1100}}

    def create_recommendations(self, tenant, dataset_id):
        if dataset_id != "DATASET-1":
            return None
        return [{"recommendation_id": "REC-1", "review_status": "待审核", "theoretical_savings_usd": 0}]

    def get_recommendations(self, tenant, dataset_id):
        return self.create_recommendations(tenant, dataset_id)


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

    def test_viewer_cannot_create_gpu_data_dataset(self):
        client = TestClient(create_app(
            lambda _token: {
                "sub": "USER-A", "organization_id": "ORG-A", "project_id": "PROJECT-A",
                "role": "VIEWER", "subscription_active": True,
            },
            store=self.store,
        ))
        response = client.post(
            "/v1/gpu-data/datasets/sample",
            headers={"Authorization": "Bearer viewer-token"},
        )
        self.assertEqual(response.status_code, 403)

    def test_sample_dataset_can_run_and_return_real_result_contract(self):
        headers = {"Authorization": "Bearer selected-token"}
        dataset = self.client.post("/v1/gpu-data/datasets/sample", headers=headers)
        self.assertEqual(dataset.status_code, 201)
        submitted = self.client.post(
            "/v1/gpu-data/datasets/DATASET-1/analyze",
            json={"idempotency_key": "sample-analysis"},
            headers=headers,
        )
        self.assertEqual(submitted.status_code, 202)
        result = self.client.get("/v1/gpu-data/datasets/DATASET-1/result", headers=headers)
        self.assertEqual(result.json()["summary"]["total_cost_usd"], 1100)

    def test_public_case_and_optimize_recommendation_contract(self):
        headers = {"Authorization": "Bearer selected-token"}
        dataset = self.client.post("/v1/gpu-data/datasets/public-case", headers=headers)
        self.assertEqual(dataset.status_code, 201)
        self.assertEqual(dataset.json()["source_type"], "PUBLIC")
        created = self.client.post("/v1/gpu-optimize/datasets/DATASET-1/recommendations", headers=headers)
        self.assertEqual(created.status_code, 201)
        self.assertEqual(created.json()["recommendations"][0]["review_status"], "待审核")
        listed = self.client.get("/v1/gpu-optimize/datasets/DATASET-1/recommendations", headers=headers)
        self.assertEqual(listed.json()["recommendations"][0]["theoretical_savings_usd"], 0)

    def test_upload_requires_exactly_four_csv_files(self):
        headers = {"Authorization": "Bearer selected-token"}
        invalid = self.client.post("/v1/gpu-data/datasets", json={"files": {}}, headers=headers)
        self.assertEqual(invalid.status_code, 422)


if __name__ == "__main__":
    unittest.main()
