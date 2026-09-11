import unittest

from saas_control.app.audit import audit_event, public_error
from saas_control.app.domain import Product, Role, TenantContext
from saas_control.app.jobs import JobService, JobStatus


class JobServiceTest(unittest.TestCase):
    def setUp(self):
        self.service = JobService()
        self.a = TenantContext("ORG-A", "PROJECT-A", "USER-A", Role.ANALYST)
        self.b = TenantContext("ORG-B", "PROJECT-B", "USER-B", Role.ANALYST)

    def test_duplicate_submission_is_idempotent_within_tenant(self):
        first = self.service.submit(self.a, Product.DATA, "SYNC", "KEY-1")
        second = self.service.submit(self.a, Product.DATA, "SYNC", "KEY-1")
        self.assertEqual(first.job_id, second.job_id)
        self.assertNotEqual(first.job_id, self.service.submit(self.b, Product.DATA, "SYNC", "KEY-1").job_id)

    def test_illegal_status_transition_is_rejected(self):
        job = self.service.submit(self.a, Product.OPTIMIZE, "SOLVE", "KEY-2")
        with self.assertRaisesRegex(ValueError, "状态"):
            self.service.transition(job.job_id, JobStatus.SUCCEEDED)

    def test_failure_and_audit_output_remove_secrets(self):
        self.assertNotIn("token", public_error(RuntimeError("token=secret-value")))
        event = audit_event(self.a, "CONNECT", "connector", "C-1", {"access_token": "secret", "count": 2})
        self.assertNotIn("access_token", event.metadata)
        self.assertEqual(event.metadata["count"], 2)


if __name__ == "__main__":
    unittest.main()
