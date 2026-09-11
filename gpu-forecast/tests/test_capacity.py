import unittest

import pandas as pd

from src.capacity import build_capacity_scenarios


class CapacityScenarioTest(unittest.TestCase):
    def test_capacity_uses_productivity_and_safety_factors(self):
        rows = build_capacity_scenarios(
            forecast=1000,
            productivity=100,
            sla_factor=1.1,
            uncertainty=1.2,
        )
        self.assertEqual(rows.iloc[0]["planned_gpu_count"], 14)

    def test_scenarios_preserve_scope_and_do_not_cross_offset(self):
        forecast = pd.DataFrame(
            [
                {"period": "2027-01-01", "team_id": "A", "workload_type": "Inference", "gpu_model": "A100", "region": "east", "p50": 500, "p90": 700, "p99": 900},
                {"period": "2027-01-01", "team_id": "B", "workload_type": "Inference", "gpu_model": "H100", "region": "west", "p50": 100, "p90": 100, "p99": 100},
            ]
        )
        rules = pd.DataFrame(
            [
                {"team_id": "A", "workload_type": "Inference", "gpu_model": "A100", "region": "east", "productivity_per_gpu": 100, "sla_safety_factor": 1, "uncertainty_factor": 1},
                {"team_id": "B", "workload_type": "Inference", "gpu_model": "H100", "region": "west", "productivity_per_gpu": 100, "sla_safety_factor": 1, "uncertainty_factor": 1},
            ]
        )
        inventory = pd.DataFrame(
            [
                {"team_id": "A", "gpu_model": "A100", "region": "east", "gpu_count": 2, "procurement_model": "OnDemand"},
                {"team_id": "B", "gpu_model": "H100", "region": "west", "gpu_count": 20, "procurement_model": "Reserved"},
            ]
        )
        result = build_capacity_scenarios(forecast, rules, inventory)
        a100 = result.query("gpu_model == 'A100' and percentile == 'P50'").iloc[0]
        self.assertEqual(a100["shortfall_gpu_count"], 3)

    def test_spot_is_not_counted_as_sla_capacity(self):
        forecast = pd.DataFrame([{"period": "2027-01-01", "team_id": "A", "workload_type": "Training", "gpu_model": "H100", "region": "east", "p50": 300, "p90": 300, "p99": 300}])
        rules = pd.DataFrame([{"team_id": "A", "workload_type": "Training", "gpu_model": "H100", "region": "east", "productivity_per_gpu": 100, "sla_safety_factor": 1, "uncertainty_factor": 1}])
        inventory = pd.DataFrame([
            {"team_id": "A", "gpu_model": "H100", "region": "east", "gpu_count": 1, "procurement_model": "Reserved"},
            {"team_id": "A", "gpu_model": "H100", "region": "east", "gpu_count": 10, "procurement_model": "Spot"},
        ])
        row = build_capacity_scenarios(forecast, rules, inventory).query("percentile == 'P50'").iloc[0]
        self.assertEqual(row["available_gpu_count"], 1)
        self.assertEqual(row["shortfall_gpu_count"], 2)

    def test_missing_capacity_rule_is_rejected(self):
        forecast = pd.DataFrame([{"period": "2027-01-01", "team_id": "A", "workload_type": "Inference", "gpu_model": "H100", "region": "east", "p50": 100, "p90": 100, "p99": 100}])
        with self.assertRaisesRegex(ValueError, "缺少容量规则"):
            build_capacity_scenarios(forecast, pd.DataFrame(), pd.DataFrame())


if __name__ == "__main__":
    unittest.main()
