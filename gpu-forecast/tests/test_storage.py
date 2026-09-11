import unittest
from pathlib import Path

from src.storage import SupabaseForecastStore


class StorageTest(unittest.TestCase):
    def test_every_user_table_has_rls(self):
        sql = Path("supabase/schema.sql").read_text(encoding="utf-8").lower()
        for table in ("projects", "forecast_jobs", "data_snapshots", "backtest_runs", "forecast_versions", "forecast_adjustments", "capacity_scenarios", "purchase_plans", "forecast_actuals"):
            self.assertIn(f"alter table {table} enable row level security", sql)
        self.assertIn("prevent_forecast_version_mutation", sql)

    def test_store_uses_authenticated_user_and_rejects_duplicate_version(self):
        store = SupabaseForecastStore(user_id="USER-1")
        saved = store.append_forecast_version({"version_id": "V1", "project_id": "P1"})
        self.assertEqual(saved["owner_id"], "USER-1")
        with self.assertRaisesRegex(ValueError, "已存在"):
            store.append_forecast_version({"version_id": "V1", "project_id": "P1", "owner_id": "OTHER"})

    def test_unauthenticated_store_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "登录"):
            SupabaseForecastStore(user_id="")


if __name__ == "__main__":
    unittest.main()
