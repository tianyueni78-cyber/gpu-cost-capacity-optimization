import unittest

import pandas as pd

from src.baseline import build_baseline


class BaselineTest(unittest.TestCase):
    def setUp(self):
        self.tables = {
            "inventory": pd.DataFrame([
                {
                    "resource_pool_id": "pool-1", "team_id": "search", "gpu_model": "H100",
                    "gpu_count": 4, "region": "us-east", "procurement_model": "ondemand",
                    "effective_hourly_rate_usd": 4.0,
                },
                {
                    "resource_pool_id": "pool-2", "team_id": "docs", "gpu_model": "A100",
                    "gpu_count": 8, "region": "us-east", "procurement_model": "reserved",
                    "effective_hourly_rate_usd": 2.0,
                },
            ]),
            "usage": pd.DataFrame([
                {"usage_record_id": "u1", "timestamp_utc": "2026-01-01T00:00:00Z", "resource_pool_id": "pool-1", "allocated_gpu_count": 4, "active_gpu_count": 1, "gpu_utilization_pct": 10},
                {"usage_record_id": "u2", "timestamp_utc": "2026-01-01T00:00:00Z", "resource_pool_id": "pool-2", "allocated_gpu_count": 8, "active_gpu_count": 3, "gpu_utilization_pct": 30},
                {"usage_record_id": "u3", "timestamp_utc": "2026-01-02T00:00:00Z", "resource_pool_id": "pool-1", "allocated_gpu_count": 4, "active_gpu_count": 4, "gpu_utilization_pct": 50},
                {"usage_record_id": "u4", "timestamp_utc": "2026-01-02T00:00:00Z", "resource_pool_id": "pool-2", "allocated_gpu_count": 8, "active_gpu_count": 8, "gpu_utilization_pct": 90},
            ]),
            "billing": pd.DataFrame([
                {"billing_line_id": "b1", "invoice_month": "2026-01", "resource_pool_id": "pool-1", "charge_type": "usage", "procurement_model": "ondemand", "gross_cost_usd": 120, "discount_usd": 20, "net_cost_usd": 100},
                {"billing_line_id": "b2", "invoice_month": "2026-01", "resource_pool_id": "pool-2", "charge_type": "usage", "procurement_model": "reserved", "gross_cost_usd": 300, "discount_usd": 50, "net_cost_usd": 250},
            ]),
            "sla": pd.DataFrame([
                {"sla_id": "s1", "team_id": "search", "workload_type": "inference", "region": "us-east", "priority_tier": "high", "min_spare_capacity_pct": 20},
                {"sla_id": "s2", "team_id": "docs", "workload_type": "batch", "region": "us-east", "priority_tier": "medium", "min_spare_capacity_pct": 10},
            ]),
        }

    def test_reconciles_cost_after_inventory_attribution(self):
        baseline = build_baseline(self.tables)
        summary = baseline["cost_summary"].iloc[0]

        self.assertEqual(420.0, summary["gross_cost_usd"])
        self.assertEqual(70.0, summary["discount_usd"])
        self.assertEqual(350.0, summary["net_cost_usd"])
        self.assertEqual(350.0, baseline["cost_breakdown"]["net_cost_usd"].sum())

    def test_reports_inventory_and_observed_usage_distribution(self):
        baseline = build_baseline(self.tables)
        capacity = baseline["capacity_summary"].iloc[0]
        usage = baseline["usage_distribution"].iloc[0]

        self.assertEqual(12.0, capacity["inventory_gpu_count"])
        self.assertEqual(6.0, capacity["median_allocated_gpu_count"])
        self.assertEqual(3.5, capacity["median_active_gpu_count"])
        self.assertAlmostEqual(7.4, capacity["p95_active_gpu_count"])
        self.assertEqual(8.0, capacity["peak_active_gpu_count"])
        self.assertEqual(40.0, usage["median_gpu_utilization_pct"])
        self.assertAlmostEqual(84.0, usage["p95_gpu_utilization_pct"])
        self.assertTrue(pd.isna(usage["median_memory_utilization_pct"]))

    def test_reports_period_telemetry_and_attribution_coverage(self):
        baseline = build_baseline(self.tables)
        coverage = baseline["coverage"].iloc[0]

        self.assertEqual(pd.Timestamp("2026-01-01T00:00:00Z"), coverage["usage_start_utc"])
        self.assertEqual(pd.Timestamp("2026-01-02T00:00:00Z"), coverage["usage_end_utc"])
        self.assertEqual(4, coverage["usage_record_count"])
        self.assertEqual(100.0, coverage["gpu_telemetry_coverage_pct"])
        self.assertTrue(pd.isna(coverage["memory_telemetry_coverage_pct"]))
        self.assertEqual(100.0, coverage["cost_attribution_coverage_pct"])
        self.assertEqual(0.0, coverage["unassigned_net_cost_usd"])


if __name__ == "__main__":
    unittest.main()
