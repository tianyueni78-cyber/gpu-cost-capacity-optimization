import unittest

import pandas as pd

from src.audit import AUDIT_COLUMNS, audit_tables


def valid_tables():
    return {
        "inventory": pd.DataFrame({
            "resource_pool_id": ["GPU-1", "GPU-2"],
            "team_id": ["TEAM-A", "TEAM-B"],
            "gpu_model": ["H100", "A100"],
            "gpu_count": [8, 4],
            "region": ["cn-east", "cn-north"],
            "procurement_model": ["OnDemand", "Reserved"],
            "effective_hourly_rate_usd": [4.0, 2.5],
        }),
        "usage": pd.DataFrame({
            "usage_record_id": ["USE-1", "USE-2"],
            "timestamp_utc": ["2026-01-01T00:00:00Z", "2026-01-01T01:00:00Z"],
            "resource_pool_id": ["GPU-1", "GPU-2"],
            "allocated_gpu_count": [8, 4],
            "active_gpu_count": [6, 3],
            "gpu_utilization_pct": [75.0, 70.0],
            "memory_utilization_pct": [None, 65.0],
        }),
        "billing": pd.DataFrame({
            "billing_line_id": ["BILL-1", "BILL-2"],
            "invoice_month": ["2026-01", "2026-01"],
            "resource_pool_id": ["GPU-1", "GPU-2"],
            "charge_type": ["Usage", "Commitment"],
            "procurement_model": ["OnDemand", "Reserved"],
            "contract_id": [None, "CONTRACT-1"],
            "gross_cost_usd": [100.0, 80.0],
            "discount_usd": [10.0, 20.0],
            "net_cost_usd": [90.0, 60.0],
        }),
        "sla": pd.DataFrame({
            "sla_id": ["SLA-1", "SLA-2"],
            "team_id": ["TEAM-A", "TEAM-B"],
            "workload_type": ["Inference", "Training"],
            "region": ["cn-east", "cn-north"],
            "priority_tier": ["P1", "P2"],
            "min_spare_capacity_pct": [20.0, 10.0],
        }),
    }


class AuditEngineTest(unittest.TestCase):
    def test_returns_stable_explainable_output(self):
        result = audit_tables(valid_tables())
        self.assertEqual(list(result.columns), AUDIT_COLUMNS)
        self.assertTrue({"通过", "异常"}.intersection(result["status"]))
        self.assertTrue(result["message"].str.len().gt(0).all())
        self.assertTrue(result["action"].str.len().gt(0).all())

    def test_detects_empty_table_and_duplicate_key(self):
        tables = valid_tables()
        tables["sla"] = tables["sla"].iloc[0:0]
        tables["inventory"] = pd.concat([tables["inventory"], tables["inventory"].iloc[[0]]], ignore_index=True)
        result = audit_tables(tables).set_index("check_id")
        self.assertEqual(result.loc["sla.table_not_empty", "severity"], "阻断")
        self.assertEqual(result.loc["inventory.unique_key", "affected_rows"], 2)

    def test_detects_missing_required_values_and_numeric_ranges(self):
        tables = valid_tables()
        tables["inventory"].loc[0, "team_id"] = None
        tables["inventory"].loc[1, "gpu_count"] = 0
        tables["usage"].loc[0, "active_gpu_count"] = 9
        tables["usage"].loc[1, "gpu_utilization_pct"] = 120
        result = audit_tables(tables).set_index("check_id")
        self.assertEqual(result.loc["inventory.required_values", "status"], "异常")
        self.assertEqual(result.loc["inventory.gpu_count_positive", "affected_rows"], 1)
        self.assertEqual(result.loc["usage.active_not_above_allocated", "affected_rows"], 1)
        self.assertEqual(result.loc["usage.gpu_utilization_range", "affected_rows"], 1)

    def test_detects_invalid_procurement_billing_formula_and_dates(self):
        tables = valid_tables()
        tables["inventory"].loc[0, "procurement_model"] = "MysteryPlan"
        tables["billing"].loc[0, "net_cost_usd"] = 95.0
        tables["billing"].loc[1, "invoice_month"] = "not-a-month"
        result = audit_tables(tables).set_index("check_id")
        self.assertEqual(result.loc["inventory.procurement_enum", "severity"], "警告")
        self.assertEqual(result.loc["billing.net_cost_formula", "severity"], "阻断")
        self.assertEqual(result.loc["billing.invoice_month_format", "affected_rows"], 1)

    def test_detects_unmatched_resource_pools(self):
        tables = valid_tables()
        tables["usage"].loc[0, "resource_pool_id"] = "GPU-404"
        tables["billing"].loc[1, "resource_pool_id"] = "GPU-405"
        result = audit_tables(tables).set_index("check_id")
        self.assertEqual(result.loc["usage.pool_linkage_normalized", "affected_rows"], 1)
        self.assertEqual(result.loc["billing.pool_linkage_normalized", "affected_rows"], 1)

    def test_detects_duplicate_usage_business_grain(self):
        tables = valid_tables()
        revision = tables["usage"].iloc[[0]].copy()
        revision["usage_record_id"] = "USE-1-R"
        tables["usage"] = pd.concat([tables["usage"], revision], ignore_index=True)
        result = audit_tables(tables).set_index("check_id")
        self.assertEqual(result.loc["usage.business_key_duplicate", "affected_rows"], 2)
        self.assertEqual(result.loc["usage.business_key_duplicate", "severity"], "阻断")

    def test_committed_purchase_requires_contract(self):
        tables = valid_tables()
        tables["billing"].loc[1, "contract_id"] = None
        result = audit_tables(tables).set_index("check_id")
        self.assertEqual(result.loc["billing.committed_contract", "affected_rows"], 1)
        self.assertEqual(result.loc["billing.committed_contract", "severity"], "阻断")

    def test_format_only_id_mismatch_warns_but_does_not_block_linkage(self):
        tables = valid_tables()
        tables["usage"].loc[0, "resource_pool_id"] = "gpu_1"
        result = audit_tables(tables).set_index("check_id")
        self.assertEqual(result.loc["usage.pool_linkage_exact", "affected_rows"], 1)
        self.assertEqual(result.loc["usage.pool_linkage_exact", "severity"], "警告")
        self.assertEqual(result.loc["usage.pool_linkage_normalized", "affected_rows"], 0)

    def test_optional_telemetry_missing_is_warning_not_zero_fill(self):
        tables = valid_tables()
        before = tables["usage"].copy(deep=True)
        result = audit_tables(tables).set_index("check_id")
        self.assertEqual(result.loc["usage.memory_utilization_pct_missing", "severity"], "警告")
        self.assertEqual(result.loc["usage.memory_utilization_pct_missing", "affected_rows"], 1)
        pd.testing.assert_frame_equal(tables["usage"], before)


if __name__ == "__main__":
    unittest.main()
