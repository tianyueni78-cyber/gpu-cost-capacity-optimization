from dataclasses import replace
from datetime import date, datetime, timezone
import unittest

from src.benefits import verify_benefit
from src.comparability import ComparabilityResult
from src.measurement import MetricSnapshot, freeze_baseline
from src.models import ActionRecord, ActionType


def action(action_type, implementation_cost_usd=100):
    return ActionRecord(
        action_id="ACT-001",
        action_type=action_type,
        resource_pool_id="GPU-001",
        owner="ops@example.com",
        approved_at=date(2026, 8, 1),
        planned_execution_at=date(2026, 8, 10),
        estimated_savings_usd=2500,
        implementation_cost_usd=implementation_cost_usd,
    )


def snapshot(**changes):
    base = MetricSnapshot(
        action_id="ACT-001",
        resource_pool_ids=("GPU-001",),
        period_start=date(2026, 7, 1),
        period_end=date(2026, 7, 31),
        currency="USD",
        cost_basis="EFFECTIVE_COST",
        volume_unit="requests",
        variable_cost_usd=8000,
        fixed_cost_usd=2000,
        business_volume=1000,
        availability_pct=99.95,
        p95_latency_ms=180,
        queue_time_seconds=4,
        failure_rate_pct=0.2,
        spare_capacity_pct=20,
        throughput_per_second=500,
        on_demand_equivalent_cost_usd=12000,
        planned_purchase_cost_usd=20000,
    )
    return replace(base, **changes)


def baseline(**changes):
    return freeze_baseline(
        snapshot(**changes),
        frozen_at=datetime(2026, 8, 1, tzinfo=timezone.utc),
    )


ALLOWED = ComparabilityResult(True, (), (), "HIGH")


class BenefitVerificationTest(unittest.TestCase):
    def test_rightsize_normalizes_variable_cost_and_preserves_fixed_cost(self):
        post = snapshot(
            period_start=date(2026, 9, 1),
            period_end=date(2026, 10, 1),
            variable_cost_usd=7200,
            fixed_cost_usd=2000,
            business_volume=1200,
        )

        result = verify_benefit(action(ActionType.RIGHTSIZE), baseline(), post, ALLOWED)

        self.assertEqual(result.counterfactual_cost_usd, 11600)
        self.assertEqual(result.actual_cost_usd, 9200)
        self.assertEqual(result.realized_savings_usd, 2300)
        self.assertEqual(result.method_id, "UNIT_COST_NORMALIZED")

    def test_rate_commitment_uses_on_demand_equivalent_cost(self):
        post = snapshot(
            period_start=date(2026, 9, 1),
            period_end=date(2026, 10, 1),
            variable_cost_usd=7600,
            fixed_cost_usd=1400,
            on_demand_equivalent_cost_usd=12000,
        )

        result = verify_benefit(
            action(ActionType.RATE_COMMITMENT, implementation_cost_usd=200),
            baseline(),
            post,
            ALLOWED,
        )

        self.assertEqual(result.realized_savings_usd, 2800)
        self.assertEqual(result.method_id, "ON_DEMAND_EQUIVALENT")

    def test_gpu_migration_requires_performance_evidence(self):
        post = snapshot(
            period_start=date(2026, 9, 1),
            period_end=date(2026, 10, 1),
            throughput_per_second=None,
        )

        result = verify_benefit(action(ActionType.GPU_MIGRATION), baseline(), post, ALLOWED)

        self.assertEqual(result.outcome, "UNVERIFIABLE")
        self.assertIn("型号替换缺少性能证据", result.reasons)

    def test_gpu_migration_rejects_material_throughput_regression(self):
        post = snapshot(
            period_start=date(2026, 9, 1), period_end=date(2026, 10, 1),
            throughput_per_second=1,
        )
        result = verify_benefit(action(ActionType.GPU_MIGRATION), baseline(), post, ALLOWED)
        self.assertEqual(result.outcome, "UNVERIFIABLE")
        self.assertIn("型号替换性能不可比", result.reasons)

    def test_scheduling_uses_unit_cost_when_operational_metrics_exist(self):
        post = snapshot(
            period_start=date(2026, 9, 1),
            period_end=date(2026, 10, 1),
            variable_cost_usd=7000,
            fixed_cost_usd=2000,
            business_volume=1000,
        )

        result = verify_benefit(action(ActionType.SCHEDULING), baseline(), post, ALLOWED)

        self.assertEqual(result.realized_savings_usd, 900)
        self.assertEqual(result.method_id, "UNIT_COST_AND_OPERATIONS")

    def test_avoided_purchase_never_counts_as_realized_savings(self):
        post = snapshot(
            period_start=date(2026, 9, 1),
            period_end=date(2026, 10, 1),
            planned_purchase_cost_usd=12000,
        )

        result = verify_benefit(
            action(ActionType.AVOIDED_PURCHASE, implementation_cost_usd=0),
            baseline(),
            post,
            ALLOWED,
        )

        self.assertEqual(result.avoided_cost_usd, 8000)
        self.assertEqual(result.realized_savings_usd, 0)
        self.assertEqual(result.method_id, "APPROVED_PURCHASE_BASELINE")

    def test_blocked_comparability_returns_no_formal_savings(self):
        blocked = ComparabilityResult(False, ("成本口径不一致",), (), "UNVERIFIABLE")

        result = verify_benefit(action(ActionType.RIGHTSIZE), baseline(), snapshot(), blocked)

        self.assertEqual(result.outcome, "UNVERIFIABLE")
        self.assertEqual(result.realized_savings_usd, 0)
        self.assertEqual(result.reasons, ("成本口径不一致",))


if __name__ == "__main__":
    unittest.main()
