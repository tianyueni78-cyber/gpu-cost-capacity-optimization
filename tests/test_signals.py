import unittest

import pandas as pd

from src.baseline import build_baseline
from src.signals import SIGNAL_COLUMNS, build_investigation_signals


class InvestigationSignalsTest(unittest.TestCase):
    def setUp(self):
        self.tables = {
            "inventory": pd.DataFrame([
                {"resource_pool_id": "pool-1", "team_id": "search", "gpu_model": "H100", "gpu_count": 4, "region": "us-east", "procurement_model": "ondemand", "effective_hourly_rate_usd": 4.0},
                {"resource_pool_id": "pool-2", "team_id": "docs", "gpu_model": "A100", "gpu_count": 8, "region": "us-east", "procurement_model": "reserved", "effective_hourly_rate_usd": 2.0, "contract_id": "contract-1", "end_date": "2026-02-15"},
                {"resource_pool_id": "pool-3", "team_id": "stable", "gpu_model": "A100", "gpu_count": 2, "region": "us-east", "procurement_model": "ondemand", "effective_hourly_rate_usd": 2.0},
            ]),
            "usage": pd.DataFrame([
                {"usage_record_id": "u1", "timestamp_utc": "2026-01-01T00:00:00Z", "resource_pool_id": "pool-1", "team_id": "search", "allocated_gpu_count": 4, "active_gpu_count": 0, "gpu_utilization_pct": 5, "availability_pct": 98.0},
                {"usage_record_id": "u2", "timestamp_utc": "2026-01-02T00:00:00Z", "resource_pool_id": "pool-1", "team_id": "search", "allocated_gpu_count": 4, "active_gpu_count": 1, "gpu_utilization_pct": 10, "availability_pct": 98.5},
                {"usage_record_id": "u3", "timestamp_utc": "2026-01-01T00:00:00Z", "resource_pool_id": "pool-2", "team_id": "docs", "allocated_gpu_count": 8, "active_gpu_count": 1, "gpu_utilization_pct": 10, "availability_pct": 100.0},
                {"usage_record_id": "u4", "timestamp_utc": "2026-01-02T00:00:00Z", "resource_pool_id": "pool-2", "team_id": "docs", "allocated_gpu_count": 8, "active_gpu_count": 1, "gpu_utilization_pct": 12, "availability_pct": 100.0},
                {"usage_record_id": "u5", "timestamp_utc": "2026-01-01T00:00:00Z", "resource_pool_id": "pool-3", "team_id": "stable", "allocated_gpu_count": 2, "active_gpu_count": 2, "gpu_utilization_pct": 80, "availability_pct": 100.0},
                {"usage_record_id": "u6", "timestamp_utc": "2026-01-02T00:00:00Z", "resource_pool_id": "pool-3", "team_id": "stable", "allocated_gpu_count": 2, "active_gpu_count": 2, "gpu_utilization_pct": 85, "availability_pct": 100.0},
            ]),
            "billing": pd.DataFrame([
                {"billing_line_id": "b1", "invoice_month": "2026-01", "resource_pool_id": "pool-1", "team_id": pd.NA, "charge_type": "usage", "procurement_model": "ondemand", "gross_cost_usd": 600, "discount_usd": 0, "net_cost_usd": 600},
                {"billing_line_id": "b2", "invoice_month": "2026-01", "resource_pool_id": "pool-2", "team_id": "docs", "charge_type": "usage", "procurement_model": "reserved", "gross_cost_usd": 500, "discount_usd": 100, "net_cost_usd": 400},
                {"billing_line_id": "b3", "invoice_month": "2026-01", "resource_pool_id": "pool-3", "team_id": "stable", "charge_type": "usage", "procurement_model": "ondemand", "gross_cost_usd": 200, "discount_usd": 0, "net_cost_usd": 200},
            ]),
            "sla": pd.DataFrame([
                {"sla_id": "s1", "team_id": "search", "workload_type": "inference", "region": "us-east", "priority_tier": "high", "min_spare_capacity_pct": 20, "availability_target_pct": 99.9},
                {"sla_id": "s2", "team_id": "docs", "workload_type": "batch", "region": "us-east", "priority_tier": "medium", "min_spare_capacity_pct": 10, "availability_target_pct": 99.0},
                {"sla_id": "s3", "team_id": "stable", "workload_type": "batch", "region": "us-east", "priority_tier": "low", "min_spare_capacity_pct": 0, "availability_target_pct": 99.0},
            ]),
        }

    def test_builds_all_five_supported_signal_types(self):
        signals = build_investigation_signals(self.tables, build_baseline(self.tables))

        self.assertEqual(
            {"high_cost_low_activity", "allocated_active_gap", "missing_attribution", "sla_constraint", "commitment_evidence"},
            set(signals["signal_type"]),
        )

    def test_clean_scope_produces_no_false_signal(self):
        clean = {name: frame[frame["resource_pool_id"].eq("pool-3")].copy() if "resource_pool_id" in frame else frame[frame["team_id"].eq("stable")].copy() for name, frame in self.tables.items()}
        signals = build_investigation_signals(clean, build_baseline(clean))

        self.assertTrue(signals.empty)
        self.assertEqual(SIGNAL_COLUMNS, list(signals.columns))

    def test_signals_preserve_evidence_and_product_boundary(self):
        signals = build_investigation_signals(self.tables, build_baseline(self.tables))

        for field in ("period", "evidence", "limitation", "question", "source_tables"):
            self.assertTrue(signals[field].astype("string").str.strip().ne("").all(), field)
        self.assertTrue(signals["affected_rows"].gt(0).all())

        rendered = " ".join(signals.astype("string").fillna("").to_numpy().ravel())
        for forbidden in ("建议释放", "预计节省", "优化方案", "未来预测"):
            self.assertNotIn(forbidden, rendered)


if __name__ == "__main__":
    unittest.main()
