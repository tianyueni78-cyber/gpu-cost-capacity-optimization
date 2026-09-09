import unittest

from src.capacity import CapacityInput, TeamRequirement
from src.scenarios import build_capacity_scenarios


class ScenarioTest(unittest.TestCase):
    def test_compares_capacity_without_claiming_unproven_savings(self):
        problem = CapacityInput(
            32,
            (TeamRequirement("search", 18, 20, 22),),
            {"search": 32},
        )

        rows = build_capacity_scenarios(problem, hourly_rate=3.0, hours=720)
        optimized = next(row for row in rows if row["scenario"] == "安全释放")

        self.assertEqual(optimized["reallocatable_gpu_count"], 10)
        self.assertEqual(optimized["affected_cost_usd"], 21600.0)
        self.assertEqual(optimized["theoretical_savings_usd"], 0.0)
        self.assertEqual(optimized["sla_shortfall_gpu_count"], 0)

    def test_infeasible_problem_returns_no_candidate_scenario(self):
        problem = CapacityInput(
            20,
            (TeamRequirement("search", 18, 20, 22),),
            {"search": 20},
        )

        rows = build_capacity_scenarios(problem, hourly_rate=3.0, hours=720)

        self.assertEqual(rows[0]["scenario"], "当前方案")
        self.assertEqual(rows[1]["scenario"], "无可行方案")
        self.assertEqual(rows[1]["sla_shortfall_gpu_count"], 2)


if __name__ == "__main__":
    unittest.main()
