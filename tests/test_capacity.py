import unittest

import pandas as pd

from src.capacity import (
    CapacityInput,
    TeamRequirement,
    build_capacity_input,
    solve_capacity,
    validate_capacity_input,
)


class CapacityInputTest(unittest.TestCase):
    def test_builds_confirmed_team_requirements(self):
        tables = {
            "inventory": pd.DataFrame([
                {"resource_pool_id": "p1", "team_id": "search", "gpu_model": "H100", "gpu_count": 32, "region": "us", "effective_hourly_rate_usd": 3.0},
            ]),
            "usage": pd.DataFrame([
                {"team_id": "search", "resource_pool_id": "p1", "active_gpu_count": 18},
            ]),
            "sla": pd.DataFrame([
                {"team_id": "search", "region": "us", "min_spare_capacity_pct": 20},
            ]),
        }

        problem = build_capacity_input(tables, {"search": 18})

        self.assertEqual(problem.teams[0].minimum_gpu_count, 22)
        self.assertEqual(problem.current_allocations, {"search": 32})
        self.assertEqual(validate_capacity_input(problem), [])

    def test_rejects_missing_demand(self):
        problem = build_capacity_input(
            {"inventory": pd.DataFrame(), "usage": pd.DataFrame(), "sla": pd.DataFrame()},
            {},
        )

        self.assertIn("至少确认一个团队需求", validate_capacity_input(problem))

    def test_solver_keeps_required_capacity_and_releases_surplus(self):
        problem = CapacityInput(
            32,
            (TeamRequirement("search", 18, 20, 22),),
            {"search": 32},
        )

        result = solve_capacity(problem)

        self.assertEqual(result.status, "optimal")
        self.assertEqual(result.team_allocations, {"search": 22})
        self.assertEqual(result.shared_gpu_count, 10)

    def test_solver_explains_capacity_shortfall(self):
        problem = CapacityInput(
            20,
            (TeamRequirement("search", 18, 20, 22),),
            {"search": 20},
        )

        result = solve_capacity(problem)

        self.assertEqual(result.status, "infeasible")
        self.assertIn("缺少 2 张 GPU", result.conflicts)


if __name__ == "__main__":
    unittest.main()
