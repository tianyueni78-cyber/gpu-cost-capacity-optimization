import unittest

import pandas as pd

from src.audit import AUDIT_COLUMNS
from src.reporting import build_csv_exports, build_markdown_report
from src.signals import SIGNAL_COLUMNS


class ReportingTest(unittest.TestCase):
    def setUp(self):
        self.baseline = {
            "cost_summary": pd.DataFrame([{"gross_cost_usd": 120.0, "discount_usd": 20.0, "net_cost_usd": 100.0}]),
            "cost_breakdown": pd.DataFrame([{"invoice_month": "2026-01", "team_id": "search", "gpu_model": "H100", "region": "us-east", "procurement_model": "ondemand", "gross_cost_usd": 120.0, "discount_usd": 20.0, "net_cost_usd": 100.0}]),
            "capacity_summary": pd.DataFrame([{"inventory_gpu_count": 4.0, "median_allocated_gpu_count": 4.0, "median_active_gpu_count": 1.0, "p95_active_gpu_count": 1.0, "peak_active_gpu_count": 1.0}]),
            "usage_distribution": pd.DataFrame([{"median_gpu_utilization_pct": 10.0, "p95_gpu_utilization_pct": 12.0, "median_memory_utilization_pct": pd.NA, "p95_memory_utilization_pct": pd.NA}]),
            "sla_summary": pd.DataFrame([{"sla_rule_count": 1, "availability_pct_coverage_pct": 100.0, "p95_latency_ms_coverage_pct": pd.NA, "queue_time_seconds_coverage_pct": pd.NA}]),
            "coverage": pd.DataFrame([{"usage_start_utc": pd.Timestamp("2026-01-01T00:00:00Z"), "usage_end_utc": pd.Timestamp("2026-01-31T00:00:00Z"), "usage_record_count": 31, "gpu_telemetry_coverage_pct": 100.0, "memory_telemetry_coverage_pct": pd.NA, "cost_attribution_coverage_pct": 100.0, "unassigned_net_cost_usd": 0.0}]),
        }
        self.signals = pd.DataFrame([{
            "signal_id": "pool-1.high_cost_low_activity", "signal_type": "high_cost_low_activity",
            "priority": "高", "scope": "pool-1", "period": "2026-01-01 至 2026-01-31",
            "observation": "高成本且持续低活跃。", "evidence": "31 条观测。",
            "affected_cost_usd": 100.0, "limitation": "低活跃不等于浪费。",
            "question": "是否存在备用要求？", "source_tables": "billing,usage", "affected_rows": 31,
        }], columns=SIGNAL_COLUMNS)
        self.audit = pd.DataFrame([{
            "check_id": "usage.memory", "table_name": "usage", "category": "完整性",
            "severity": "警告", "status": "异常", "affected_rows": 31, "total_rows": 31,
            "message": "缺少显存指标。", "action": "补充显存遥测。",
        }], columns=AUDIT_COLUMNS)
        self.metadata = {
            "analysis_period": "2026-01-01 至 2026-01-31",
            "generated_at": "2026-09-09T12:00:00+08:00",
        }

    def test_markdown_contains_decision_context_and_limitations(self):
        report = build_markdown_report(self.baseline, self.signals, self.audit, self.metadata)

        for expected in (
            "2026-01-01 至 2026-01-31", "净成本", "$100.00", "成本对账",
            "数据覆盖", "缺少显存指标", "指标口径", "调查线索",
            "低活跃不等于浪费", "2026-09-09T12:00:00+08:00",
        ):
            self.assertIn(expected, report)

    def test_csv_exports_use_utf8_bom_and_stable_columns(self):
        exports = build_csv_exports(self.baseline, self.signals, self.audit)

        self.assertEqual({"metrics.csv", "signals.csv", "data_quality.csv"}, set(exports))
        for content in exports.values():
            self.assertTrue(content.startswith(b"\xef\xbb\xbf"))
        self.assertEqual("section,metric,value", exports["metrics.csv"].decode("utf-8-sig").splitlines()[0])
        self.assertEqual(",".join(SIGNAL_COLUMNS), exports["signals.csv"].decode("utf-8-sig").splitlines()[0])
        self.assertEqual(",".join(AUDIT_COLUMNS), exports["data_quality.csv"].decode("utf-8-sig").splitlines()[0])


if __name__ == "__main__":
    unittest.main()
