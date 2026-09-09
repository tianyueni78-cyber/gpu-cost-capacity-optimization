import unittest

from src.capacity import CapacityInput, CapacitySolution, PoolAdjustment, ResourcePool, TeamRequirement
from src.recommendations import build_recommendations, set_recommendation_status


class RecommendationTest(unittest.TestCase):
    def test_recommendation_contains_complete_decision_evidence(self):
        problem = CapacityInput(
            (ResourcePool("p1", "search", "H100", "us", 8, 4, "team", True),),
            (TeamRequirement("search", "H100", "us", 6, 0, 6),),
        )
        solution = CapacitySolution(
            "optimal", (PoolAdjustment("p1", 6, 0, 2),), {("H100", "us"): 0}, ()
        )
        scenarios = {
            "scenarios": [{"scenario": "安全调整", "affected_cost_usd": 5760}],
            "pool_adjustments": [{"resource_pool_id": "p1"}],
        }

        item = build_recommendations(problem, solution, scenarios, "2026-08")[0]

        required = {
            "affected_resources", "period", "current_configuration",
            "proposed_configuration", "constraints_met", "sla_risk",
            "limitation", "owner_question",
        }
        self.assertTrue(required.issubset(item))
        self.assertEqual(item["status"], "待审批")

    def test_unconfirmed_sharing_boundary_waits_for_confirmation(self):
        problem = CapacityInput(
            (ResourcePool("p1", "search", "H100", "us", 8, 4, "none", False),),
            (),
        )
        solution = CapacitySolution("optimal", (), {("H100", "us"): 0}, ())

        item = build_recommendations(problem, solution, {"scenarios": [], "pool_adjustments": []}, "2026-08")[0]

        self.assertEqual(item["status"], "待确认")

    def test_status_update_changes_metadata_only(self):
        items = [{"recommendation_id": "H100-us", "status": "待审批", "affected_cost_usd": 10}]

        changed = set_recommendation_status(items, "H100-us", "推迟")

        self.assertEqual(changed[0]["status"], "推迟")
        self.assertEqual(changed[0]["affected_cost_usd"], 10)
        self.assertEqual(items[0]["status"], "待审批")

    def test_missing_team_demand_waits_for_confirmation(self):
        problem = CapacityInput(
            (ResourcePool("p1", "search", "H100", "us", 8, 4, "team", True),),
            (),
        )
        solution = CapacitySolution(
            "optimal", (PoolAdjustment("p1", 8, 0, 0),), {("H100", "us"): 0}, ()
        )

        item = build_recommendations(problem, solution, {"scenarios": [], "pool_adjustments": []}, "2026-08")[0]

        self.assertEqual(item["status"], "待确认")


if __name__ == "__main__":
    unittest.main()
