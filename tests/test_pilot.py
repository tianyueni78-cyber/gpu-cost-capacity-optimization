import unittest
from pathlib import Path

import pandas as pd

from pilot import build_actions, build_executive_report, load_pilot


class PilotTest(unittest.TestCase):
    def sample(self):
        return {
            "project": {"project_id": "P-1", "customer": "示例客户", "analysis_period": "2026-08", "currency": "USD"},
            "metrics": pd.DataFrame([
                {"section": "cost_summary", "metric": "net_cost_usd", "value": 12000},
            ]),
            "signals": pd.DataFrame([
                {"scope": "pool-a", "affected_cost_usd": 4000, "observation": "低利用率"},
            ]),
            "data_quality": pd.DataFrame([
                {"severity": "警告", "status": "异常", "message": "显存遥测缺失"},
            ]),
            "recommendations": pd.DataFrame([
                {"recommendation_id": "H100-us", "status": "待审批", "affected_resources": "pool-a, pool-b", "affected_cost_usd": 3000, "sla_risk": "低"},
                {"recommendation_id": "A100-us", "status": "待确认", "affected_resources": "pool-c", "affected_cost_usd": 1000, "sla_risk": "待确认"},
            ]),
            "scenarios": pd.DataFrame([{"scenario": "安全调整", "affected_cost_usd": 3000}]),
            "approvals": pd.DataFrame([
                {"recommendation_id": "H100-us", "owner": "ops@example.com", "approved_at": "2026-09-01", "planned_execution_at": "2026-09-08", "implementation_cost_usd": 100},
            ]),
            "benefits": pd.DataFrame([
                {"已验证收益（USD）": 700, "成本规避（USD）": 200, "SLA结论": "通过", "原因": ""},
            ]),
        }

    def test_build_actions_only_uses_explicit_approvals(self):
        actions = build_actions(self.sample())
        self.assertEqual(list(actions["resource_pool_id"]), ["pool-a", "pool-b"])
        self.assertTrue((actions["estimated_savings_usd"] == 0).all())
        self.assertTrue((actions["action_type"] == "RIGHTSIZE").all())
        self.assertEqual(actions["implementation_cost_usd"].sum(), 100)

    def test_report_separates_affected_cost_realized_savings_and_avoided_cost(self):
        report = build_executive_report(self.sample())
        self.assertIn("$12,000.00", report)
        self.assertIn("受影响成本：$3,000.00", report)
        self.assertIn("已验证收益：$700.00", report)
        self.assertIn("成本规避：$200.00", report)
        self.assertIn("显存遥测缺失", report)

    def test_report_does_not_add_mutually_exclusive_scenarios(self):
        data = self.sample()
        data["scenarios"] = pd.DataFrame([
            {"scenario": "安全调整", "affected_cost_usd": 3000},
            {"scenario": "低变更", "affected_cost_usd": 1500},
        ])
        report = build_executive_report(data)
        self.assertIn("受影响成本：$3,000.00", report)
        self.assertNotIn("$4,500.00", report)

    def test_load_requires_every_core_file(self):
        with self.assertRaisesRegex(ValueError, "缺少试点文件"):
            load_pilot(Path("missing-pilot-test-dir"))


if __name__ == "__main__":
    unittest.main()
