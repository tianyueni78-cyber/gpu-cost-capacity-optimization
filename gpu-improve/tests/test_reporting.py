from io import BytesIO
import unittest

import pandas as pd

from src.benefits import BenefitResult
from src.reporting import build_ledger, export_csv_bytes, render_executive_report


def result(action_id, realized=0, avoided=0, outcome="VERIFIED", reasons=()):
    return BenefitResult(
        action_id=action_id,
        method_id="UNIT_COST_NORMALIZED",
        formula_version="1.0",
        counterfactual_cost_usd=10000,
        actual_cost_usd=9000,
        implementation_cost_usd=100,
        realized_savings_usd=realized,
        avoided_cost_usd=avoided,
        evidence_grade="HIGH" if outcome == "VERIFIED" else "UNVERIFIABLE",
        outcome=outcome,
        reasons=reasons,
    )


class ReportingTest(unittest.TestCase):
    def test_avoided_cost_is_not_summed_as_realized_savings(self):
        ledger = build_ledger(
            [result("ACT-1", realized=1000), result("ACT-2", avoided=5000)],
            action_details={
                "ACT-1": {"project": "试点", "owner": "张三", "status": "VERIFIED", "estimated_savings_usd": 1200},
                "ACT-2": {"project": "试点", "owner": "李四", "status": "VERIFIED", "estimated_savings_usd": 5000},
            },
        )

        self.assertEqual(ledger["已验证收益（USD）"].sum(), 1000)
        self.assertEqual(ledger["成本规避（USD）"].sum(), 5000)
        self.assertEqual(list(ledger.columns)[0:3], ["项目", "行动编号", "负责人"])

    def test_csv_uses_utf8_bom(self):
        payload = export_csv_bytes(build_ledger([result("ACT-1", realized=1000)]))

        self.assertTrue(payload.startswith(b"\xef\xbb\xbf"))
        decoded = pd.read_csv(BytesIO(payload))
        self.assertEqual(decoded.iloc[0]["已验证收益（USD）"], 1000)

    def test_report_leads_with_conclusion_and_keeps_risks(self):
        ledger = build_ledger(
            [
                result("ACT-1", realized=1000),
                result("ACT-2", outcome="UNVERIFIABLE", reasons=("缺少SLA或安全容量指标",)),
            ]
        )

        report = render_executive_report(ledger)

        self.assertTrue(report.startswith("# 管理层收益复盘\n\n## 结论"))
        self.assertIn("证据等级", report)
        self.assertIn("缺少SLA或安全容量指标", report)
        self.assertIn("验证方法", report)


if __name__ == "__main__":
    unittest.main()
