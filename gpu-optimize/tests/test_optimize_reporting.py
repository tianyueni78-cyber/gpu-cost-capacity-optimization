import unittest

from src.optimize_reporting import build_approval_report, rows_csv


class ReportingTest(unittest.TestCase):
    def test_report_marks_cost_scope_and_customer_decision(self):
        report = build_approval_report(
            {"period": "2026-08"},
            [{"scenario": "安全释放", "affected_cost_usd": 21600, "theoretical_savings_usd": 0}],
            ["20% 备用容量"],
            [{"recommendation_id": "H100-us", "status": "待审批", "affected_resources": "p1", "sla_risk": "低", "owner_question": "是否批准？"}],
            [{"resource_pool_id": "p1", "releasable_gpu_count": 2}],
        )

        self.assertIn("受影响成本", report)
        self.assertIn("不是已验证节省", report)
        self.assertIn("客户负责人审批", report)
        self.assertIn("回滚", report)

    def test_csv_is_excel_compatible(self):
        content = rows_csv([{"scenario": "当前方案"}])

        self.assertTrue(content.startswith(b"\xef\xbb\xbf"))


if __name__ == "__main__":
    unittest.main()
