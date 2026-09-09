import unittest

from src.capacity import CapacityInput, CapacitySolution, PoolAdjustment, ResourcePool
from src.scenarios import build_capacity_scenarios


class ScenarioTest(unittest.TestCase):
    def test_affected_cost_uses_each_adjusted_pool_rate(self):
        problem = CapacityInput(
            pools=(
                ResourcePool("cheap", "a", "H100", "us", 4, 1.0, "team"),
                ResourcePool("expensive", "a", "H100", "us", 4, 4.0, "team"),
            ),
            requirements=(),
        )
        solution = CapacitySolution(
            "optimal",
            (
                PoolAdjustment("cheap", 3, 0, 1),
                PoolAdjustment("expensive", 2, 0, 2),
            ),
            {("H100", "us"): 0},
            (),
        )

        result = build_capacity_scenarios(problem, solution, period_hours=100)
        safe = next(row for row in result["scenarios"] if row["scenario"] == "安全调整")

        self.assertEqual(safe["affected_cost_usd"], 900.0)
        self.assertEqual(
            sum(row["affected_cost_usd"] for row in result["pool_adjustments"]),
            900.0,
        )
        self.assertEqual(safe["theoretical_savings_usd"], 0.0)

    def test_pool_details_keep_compatibility_evidence(self):
        problem = CapacityInput(
            (ResourcePool("p1", "search", "A100", "eu", 8, 2.0, "cross_team"),),
            (),
        )
        solution = CapacitySolution(
            "optimal", (PoolAdjustment("p1", 6, 2, 2),), {("A100", "eu"): 2}, ()
        )

        detail = build_capacity_scenarios(problem, solution, 10)["pool_adjustments"][0]

        self.assertEqual(detail["gpu_model"], "A100")
        self.assertEqual(detail["region"], "eu")
        self.assertEqual(detail["sharing_scope"], "cross_team")


if __name__ == "__main__":
    unittest.main()
