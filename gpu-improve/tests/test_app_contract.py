from pathlib import Path
import unittest

from src.comparability import ComparabilityResult
from src.workflow import can_verify, current_actor, database_configured, persist_then_export, read_metric_snapshot


class AppContractTest(unittest.TestCase):
    def test_actor_is_authenticated_user_not_action_owner(self):
        self.assertEqual(current_actor({"user_id": "USER-A"}), "USER-A")
        self.assertEqual(current_actor({}), "local-demo-user")

    def test_missing_secrets_enters_demo_mode(self):
        class MissingSecrets:
            def get(self, key):
                raise RuntimeError("No secrets found")

        self.assertFalse(database_configured(MissingSecrets()))

    def test_app_exposes_only_four_improve_pages(self):
        source = Path("app.py").read_text(encoding="utf-8")
        for page in ("行动导入", "执行台账", "收益验证", "收益复盘"):
            self.assertIn(page, source)
        self.assertNotIn("自动执行生产变更", source)

    def test_blocking_reason_prevents_verification(self):
        blocked = ComparabilityResult(False, ("币种不一致",), (), "UNVERIFIABLE")
        self.assertFalse(can_verify(blocked))

    def test_result_is_persisted_before_export(self):
        calls = []

        output = persist_then_export(
            {"action_id": "ACT-1"},
            save=lambda value: calls.append(("save", value)),
            export=lambda value: calls.append(("export", value)) or b"csv",
        )

        self.assertEqual([name for name, _ in calls], ["save", "export"])
        self.assertEqual(output, b"csv")

    def test_metric_csv_becomes_real_snapshot(self):
        payload = (
            b"action_id,resource_pool_ids,period_start,period_end,currency,cost_basis,volume_unit,"
            b"variable_cost_usd,fixed_cost_usd,business_volume\n"
            b"ACT-1,GPU-1,2026-01-01,2026-01-31,USD,EFFECTIVE_COST,requests,10,2,100\n"
        )
        result = read_metric_snapshot(payload, "ACT-1")
        self.assertEqual(result.resource_pool_ids, ("GPU-1",))
        self.assertEqual(result.effective_cost_usd, 12)


if __name__ == "__main__":
    unittest.main()
