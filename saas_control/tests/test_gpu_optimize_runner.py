import unittest

from saas_control.app.gpu_optimize_runner import build_recommendations


class GpuOptimizeRunnerTest(unittest.TestCase):
    def test_signal_becomes_auditable_recommendation_without_claiming_savings(self):
        result = {
            "result_id": "RESULT-1",
            "dataset_id": "DATASET-1",
            "status": "SUCCEEDED",
            "summary": {"gpu_telemetry_coverage_pct": 87.5},
            "signals": [{
                "signal_id": "pool-1.allocated_active_gap",
                "signal_type": "allocated_active_gap",
                "scope": "pool-1",
                "period": "2020-07-01 至 2020-07-31",
                "evidence": "已分配 4，活跃 1。",
                "affected_cost_usd": 100,
                "limitation": "快照不能证明容量可回收。",
            }],
        }
        item = build_recommendations(result)[0]
        self.assertEqual(item["related_cost_usd"], 100)
        self.assertEqual(item["theoretical_savings_usd"], 0)
        self.assertEqual(item["review_status"], "待审核")
        self.assertEqual(item["evidence_coverage_pct"], 87.5)
        self.assertEqual(item["source_result_id"], "RESULT-1")
        self.assertIn("不能", item["limitations"])

    def test_blocked_result_never_generates_recommendations(self):
        self.assertEqual(build_recommendations({"status": "BLOCKED", "signals": []}), [])


if __name__ == "__main__":
    unittest.main()
