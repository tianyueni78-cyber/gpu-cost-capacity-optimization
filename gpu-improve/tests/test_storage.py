from pathlib import Path
import unittest

from src.storage import StorageError, SupabaseStore


class FakeQuery:
    def __init__(self, client, table):
        self.client = client
        self.table = table
        self.payload = None
        self.filters = []

    def insert(self, payload):
        self.payload = payload
        return self

    def select(self, columns):
        return self

    def eq(self, field, value):
        self.filters.append((field, value))
        return self

    def execute(self):
        self.client.calls.append((self.table, self.payload, tuple(self.filters)))
        return type("Response", (), {"data": [self.payload or {"project_id": "P-1"}]})()


class FakeClient:
    def __init__(self):
        self.calls = []

    def table(self, name):
        return FakeQuery(self, name)


class SchemaSecurityTest(unittest.TestCase):
    def test_schema_enables_rls_for_every_user_table(self):
        sql = Path("supabase/schema.sql").read_text(encoding="utf-8").lower()
        for table in (
            "projects", "actions", "action_events", "baselines", "measurements", "benefit_results"
        ):
            self.assertIn(f"alter table {table} enable row level security", sql)
            self.assertIn(f"on {table}", sql)

        self.assertIn("auth.uid()", sql)
        self.assertIn("prevent_baseline_mutation", sql)


class StorageContractTest(unittest.TestCase):
    def test_requires_authenticated_user(self):
        with self.assertRaises(StorageError):
            SupabaseStore(FakeClient(), user_id="")

    def test_create_project_uses_authenticated_user_as_owner(self):
        client = FakeClient()
        store = SupabaseStore(client, user_id="USER-1")

        store.create_project("项目一")

        self.assertEqual(client.calls[0][0], "projects")
        self.assertEqual(client.calls[0][1]["owner_id"], "USER-1")

    def test_child_writes_do_not_accept_owner_override(self):
        client = FakeClient()
        store = SupabaseStore(client, user_id="USER-1")

        store.save_action("P-1", {"action_id": "ACT-1", "owner_id": "ATTACKER"})

        payload = client.calls[0][1]
        self.assertEqual(payload["project_id"], "P-1")
        self.assertNotIn("owner_id", payload)

    def test_database_error_does_not_expose_secret(self):
        class BrokenClient:
            def table(self, name):
                raise RuntimeError("secret-service-role-key")

        store = SupabaseStore(BrokenClient(), user_id="USER-1")
        with self.assertRaisesRegex(StorageError, "数据库操作失败") as error:
            store.create_project("项目一")
        self.assertNotIn("secret-service-role-key", str(error.exception))


if __name__ == "__main__":
    unittest.main()
