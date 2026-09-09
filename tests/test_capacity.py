import unittest

import pandas as pd

from src.capacity import build_capacity_input, peak_demands, solve_capacity, validate_capacity_input


def tables(inventory_rows, sla_rows=None):
    return {
        "inventory": pd.DataFrame(inventory_rows),
        "usage": pd.DataFrame(),
        "sla": pd.DataFrame(sla_rows or []),
    }


class CapacityInputTest(unittest.TestCase):
    def test_builds_separate_model_and_region_requirements(self):
        source = tables(
            [
                {"resource_pool_id": "h", "team_id": "search", "gpu_model": "H100", "region": "us-east", "gpu_count": 10, "effective_hourly_rate_usd": 4},
                {"resource_pool_id": "a", "team_id": "search", "gpu_model": "A100", "region": "us-east", "gpu_count": 8, "effective_hourly_rate_usd": 2},
            ],
            [{"team_id": "search", "region": "us-east", "min_spare_capacity_pct": 20}],
        )
        problem = build_capacity_input(
            source,
            {("search", "H100", "us-east"): 8, ("search", "A100", "us-east"): 4},
            {"h": "cross_team", "a": "team"},
        )

        self.assertEqual({item.scope for item in problem.requirements}, {("H100", "us-east"), ("A100", "us-east")})
        self.assertEqual(problem.pools[0].sharing_scope, "cross_team")

    def test_missing_sharing_scope_defaults_to_none(self):
        source = tables([
            {"resource_pool_id": "h", "team_id": "search", "gpu_model": "H100", "region": "us", "gpu_count": 10, "effective_hourly_rate_usd": 4},
        ])
        problem = build_capacity_input(source, {("search", "H100", "us"): 8}, {})
        self.assertEqual(problem.pools[0].sharing_scope, "none")

    def test_validation_rejects_unknown_scope_and_missing_inventory_scope(self):
        source = tables([
            {"resource_pool_id": "h", "team_id": "search", "gpu_model": "H100", "region": "us", "gpu_count": 10, "effective_hourly_rate_usd": 4},
        ])
        problem = build_capacity_input(source, {("search", "A100", "us"): 8}, {"h": "everyone"})
        errors = validate_capacity_input(problem)
        self.assertIn("资源池 h 的共享范围无效", errors)
        self.assertIn("需求 search / A100 / us 没有匹配的库存", errors)

    def test_peak_demands_are_scoped_by_team_model_and_region(self):
        inventory = pd.DataFrame([
            {"resource_pool_id": "h", "team_id": "search", "gpu_model": "H100", "region": "us"},
            {"resource_pool_id": "a", "team_id": "search", "gpu_model": "A100", "region": "us"},
        ])
        usage = pd.DataFrame([
            {"resource_pool_id": "h", "active_gpu_count": 7},
            {"resource_pool_id": "a", "active_gpu_count": 3},
        ])
        self.assertEqual(
            peak_demands(inventory, usage),
            {("search", "A100", "us"): 3, ("search", "H100", "us"): 7},
        )

    def test_h100_cannot_cover_a100_shortfall(self):
        source = tables([
            {"resource_pool_id": "h", "team_id": "search", "gpu_model": "H100", "region": "us", "gpu_count": 10, "effective_hourly_rate_usd": 4},
            {"resource_pool_id": "a", "team_id": "docs", "gpu_model": "A100", "region": "us", "gpu_count": 2, "effective_hourly_rate_usd": 2},
        ])
        problem = build_capacity_input(source, {("docs", "A100", "us"): 4}, {"h": "cross_team", "a": "cross_team"})
        result = solve_capacity(problem)
        self.assertEqual(result.status, "infeasible")
        self.assertIn("docs / A100 / us 缺少 2 张 GPU", result.conflicts)

    def test_team_scope_cannot_move_capacity_to_another_team(self):
        source = tables([
            {"resource_pool_id": "search-h", "team_id": "search", "gpu_model": "H100", "region": "us", "gpu_count": 6, "effective_hourly_rate_usd": 4},
            {"resource_pool_id": "docs-h", "team_id": "docs", "gpu_model": "H100", "region": "us", "gpu_count": 2, "effective_hourly_rate_usd": 4},
        ])
        problem = build_capacity_input(
            source,
            {("search", "H100", "us"): 2, ("docs", "H100", "us"): 4},
            {"search-h": "team", "docs-h": "team"},
        )
        result = solve_capacity(problem)
        self.assertEqual(result.status, "infeasible")
        self.assertIn("docs / H100 / us 缺少 2 张 GPU", result.conflicts)

    def test_cross_team_scope_can_fill_compatible_shortfall(self):
        source = tables([
            {"resource_pool_id": "search-h", "team_id": "search", "gpu_model": "H100", "region": "us", "gpu_count": 6, "effective_hourly_rate_usd": 4},
            {"resource_pool_id": "docs-h", "team_id": "docs", "gpu_model": "H100", "region": "us", "gpu_count": 2, "effective_hourly_rate_usd": 4},
        ])
        problem = build_capacity_input(
            source,
            {("search", "H100", "us"): 2, ("docs", "H100", "us"): 4},
            {"search-h": "cross_team", "docs-h": "team"},
        )
        result = solve_capacity(problem)
        adjustment = next(item for item in result.adjustments if item.resource_pool_id == "search-h")
        self.assertEqual(result.status, "optimal")
        self.assertEqual(adjustment.cross_team_shared_gpu_count, 2)

    def test_infeasible_scope_does_not_hide_feasible_scope(self):
        source = tables([
            {"resource_pool_id": "a", "team_id": "docs", "gpu_model": "A100", "region": "us", "gpu_count": 1, "effective_hourly_rate_usd": 2},
            {"resource_pool_id": "h", "team_id": "search", "gpu_model": "H100", "region": "us", "gpu_count": 6, "effective_hourly_rate_usd": 4},
        ])
        problem = build_capacity_input(
            source,
            {("docs", "A100", "us"): 2, ("search", "H100", "us"): 2},
            {"a": "team", "h": "team"},
        )

        result = solve_capacity(problem)

        self.assertEqual(result.status, "infeasible")
        self.assertTrue(any(item.resource_pool_id == "h" for item in result.adjustments))


if __name__ == "__main__":
    unittest.main()
