import unittest
from pathlib import Path

import pandas as pd

from src.contracts import ForecastInputs, ForecastScope
from src.readiness import assess_readiness, read_forecast_inputs


def scope() -> ForecastScope:
    return ForecastScope(
        team_ids=("TEAM-A",),
        gpu_models=("H100-80GB",),
        regions=("cn-east-1",),
        period_start="2025-01-01",
        period_end="2025-12-01",
    )


def valid_inputs(periods=12) -> ForecastInputs:
    history = pd.DataFrame(
        {
            "period": pd.date_range("2025-01-01", periods=periods, freq="MS"),
            "team_id": "TEAM-A",
            "workload_type": "Inference",
            "gpu_model": "H100-80GB",
            "region": "cn-east-1",
            "business_volume": range(100, 100 + periods),
            "volume_unit": "requests",
            "event_flag": False,
        }
    )
    inventory = pd.DataFrame(
        {
            "resource_pool_id": ["GPU-001"],
            "team_id": ["TEAM-A"],
            "gpu_model": ["H100-80GB"],
            "region": ["cn-east-1"],
            "gpu_count": [8],
            "procurement_model": ["OnDemand"],
            "start_date": [pd.Timestamp("2024-01-01")],
            "end_date": [pd.NaT],
        }
    )
    rules = pd.DataFrame(
        {
            "team_id": ["TEAM-A"],
            "workload_type": ["Inference"],
            "gpu_model": ["H100-80GB"],
            "region": ["cn-east-1"],
            "productivity_per_gpu": [1000.0],
            "sla_safety_factor": [1.1],
            "min_spare_capacity_pct": [10.0],
        }
    )
    return ForecastInputs(history, inventory, rules)


class ReadinessTest(unittest.TestCase):
    def test_complete_continuous_history_is_high_evidence(self):
        result = assess_readiness(valid_inputs(), scope())
        self.assertTrue(result.allowed)
        self.assertEqual(result.evidence_grade, "HIGH")
        self.assertEqual(result.blocking_reasons, ())

    def test_missing_history_period_blocks_formal_forecast(self):
        inputs = valid_inputs()
        history = inputs.business_history.drop(index=5).reset_index(drop=True)
        result = assess_readiness(
            ForecastInputs(history, inputs.resource_inventory, inputs.capacity_rules),
            scope(),
        )
        self.assertFalse(result.allowed)
        self.assertIn("历史时间不连续", result.blocking_reasons)

    def test_unit_change_without_segment_is_blocked(self):
        inputs = valid_inputs()
        history = inputs.business_history.copy()
        history.loc[6:, "volume_unit"] = "tokens"
        result = assess_readiness(
            ForecastInputs(history, inputs.resource_inventory, inputs.capacity_rules),
            scope(),
        )
        self.assertIn("业务量单位在范围内发生变化", result.blocking_reasons)

    def test_short_history_missing_link_and_rule_are_blocked(self):
        inputs = valid_inputs(periods=11)
        history = inputs.business_history.assign(team_id="TEAM-X")
        result = assess_readiness(
            ForecastInputs(history, inputs.resource_inventory, inputs.capacity_rules.iloc[0:0]),
            ForecastScope(
                team_ids=("TEAM-X",),
                gpu_models=("H100-80GB",),
                regions=("cn-east-1",),
                period_start="2025-01-01",
                period_end="2025-11-01",
            ),
        )
        self.assertEqual(result.evidence_grade, "UNVERIFIABLE")
        self.assertIn("连续历史少于12个周期", result.blocking_reasons)
        self.assertIn("预测范围无法关联资源清单", result.blocking_reasons)
        self.assertIn("预测范围缺少容量换算规则", result.blocking_reasons)

    def test_event_peak_is_preserved_and_warned(self):
        inputs = valid_inputs()
        history = inputs.business_history.copy()
        history.loc[5, ["business_volume", "event_flag"]] = [9999, True]
        adjusted = ForecastInputs(history, inputs.resource_inventory, inputs.capacity_rules)
        result = assess_readiness(adjusted, scope())
        self.assertTrue(result.allowed)
        self.assertEqual(result.evidence_grade, "MEDIUM")
        self.assertIn("历史包含已标记业务事件峰值，已保留", result.warnings)
        self.assertEqual(adjusted.business_history.loc[5, "business_volume"], 9999)

    def test_csv_reader_parses_dates_numbers_and_boolean(self):
        root = Path("examples")
        loaded = read_forecast_inputs(
            {
                "business_history": root / "business_history.csv",
                "resource_inventory": root / "resource_inventory.csv",
                "capacity_rules": root / "capacity_rules.csv",
            }
        )

        self.assertTrue(pd.api.types.is_datetime64_any_dtype(loaded.business_history["period"]))
        self.assertTrue(pd.api.types.is_numeric_dtype(loaded.business_history["business_volume"]))
        self.assertEqual(bool(loaded.business_history.loc[0, "event_flag"]), False)


if __name__ == "__main__":
    unittest.main()
