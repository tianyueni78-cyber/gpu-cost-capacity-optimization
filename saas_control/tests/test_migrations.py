import unittest
from pathlib import Path


class MigrationContractTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sql = Path("saas_control/migrations/001_control_plane.sql").read_text(encoding="utf-8").lower()

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


if __name__ == "__main__":
    unittest.main()
