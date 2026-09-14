import unittest
from pathlib import Path


class MigrationContractTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sql = Path("saas_control/migrations/001_control_plane.sql").read_text(encoding="utf-8").lower()
        cls.gpu_data_sql = Path("saas_control/migrations/003_gpu_data.sql").read_text(encoding="utf-8").lower()
        cls.optimize_sql = Path("saas_control/migrations/004_public_optimize.sql").read_text(encoding="utf-8").lower()

    def test_control_plane_tables_enable_rls(self):
        tables = ("organizations", "memberships", "projects", "product_entitlements", "subscriptions", "connectors", "jobs", "audit_events")
        for table in tables:
            self.assertIn(f"create table if not exists {table}", self.sql)
            self.assertIn(f"alter table {table} enable row level security", self.sql)

    def test_tenant_children_use_composite_foreign_keys(self):
        self.assertIn("foreign key (organization_id, project_id)", self.sql)
        self.assertIn("unique (organization_id, project_id)", self.sql)

    def test_audit_events_are_append_only(self):
        self.assertIn("prevent_audit_mutation", self.sql)
        self.assertIn("before update or delete on audit_events", self.sql)

    def test_rls_uses_authenticated_membership(self):
        self.assertIn("auth.uid()", self.sql)
        self.assertIn("is_organization_member", self.sql)

    def test_gpu_data_tables_are_tenant_scoped_and_rls_enabled(self):
        for table in ("datasets", "dataset_files", "analysis_results", "report_artifacts"):
            self.assertIn(f"create table if not exists {table}", self.gpu_data_sql)
            self.assertIn(f"alter table {table} enable row level security", self.gpu_data_sql)
        self.assertGreaterEqual(self.gpu_data_sql.count("foreign key (organization_id, project_id)"), 4)

    def test_optimize_recommendations_are_tenant_scoped_and_rls_enabled(self):
        self.assertIn("create table if not exists optimization_recommendations", self.optimize_sql)
        self.assertIn("foreign key (organization_id, project_id)", self.optimize_sql)
        self.assertIn("alter table optimization_recommendations enable row level security", self.optimize_sql)


if __name__ == "__main__":
    unittest.main()
