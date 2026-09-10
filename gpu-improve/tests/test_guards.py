from dataclasses import replace
from datetime import date, datetime, timezone
import unittest

from src.benefits import verify_benefit
from src.comparability import ComparabilityResult
from src.guards import (
    ActionScope,
    SideEffectThresholds,
    evaluate_side_effects,
    finalize_result,
    find_overlaps,
)
from src.measurement import MetricSnapshot, freeze_baseline
from src.models import ActionRecord, ActionType


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
    )
    return replace(base, **changes)


def benefit():
    action = ActionRecord(
        action_id="ACT-001",
        action_type=ActionType.RIGHTSIZE,
        resource_pool_id="GPU-001",
        owner="ops@example.com",
        approved_at=date(2026, 8, 1),
        planned_execution_at=date(2026, 8, 10),
        estimated_savings_usd=2000,
        implementation_cost_usd=100,
    )
    before = freeze_baseline(snapshot(), datetime(2026, 8, 1, tzinfo=timezone.utc))
    after = snapshot(
        period_start=date(2026, 9, 1),
        period_end=date(2026, 10, 1),
        variable_cost_usd=7000,
    )
    return verify_benefit(action, before, after, ComparabilityResult(True, (), (), "HIGH"))


class OverlapGuardTest(unittest.TestCase):
    def test_finds_overlapping_actions_on_same_resource(self):
        scopes = (
            ActionScope("ACT-001", "GPU-001", date(2026, 8, 1), date(2026, 8, 31)),
            ActionScope("ACT-002", "GPU-001", date(2026, 8, 15), date(2026, 9, 15)),
        )

        overlaps = find_overlaps(scopes)

        self.assertEqual(overlaps[0].action_ids, ("ACT-001", "ACT-002"))

    def test_ignores_non_overlapping_actions(self):
        scopes = (
            ActionScope("ACT-001", "GPU-001", date(2026, 8, 1), date(2026, 8, 10)),
            ActionScope("ACT-002", "GPU-001", date(2026, 8, 11), date(2026, 8, 20)),
        )

        self.assertEqual(find_overlaps(scopes), ())


class SideEffectGuardTest(unittest.TestCase):
    def setUp(self):
        self.thresholds = SideEffectThresholds(
            min_availability_pct=99.9,
            max_p95_latency_ms=200,
            max_queue_time_seconds=5,
            max_failure_rate_pct=0.5,
            min_spare_capacity_pct=10,
        )

    def test_savings_with_sla_breach_is_negative_impact(self):
        side_effect = evaluate_side_effects(
            snapshot(), snapshot(availability_pct=99.5), self.thresholds
        )

        result = finalize_result(benefit(), (), side_effect)

        self.assertEqual(result.outcome, "NEGATIVE_IMPACT")
        self.assertIn("可用性低于最低阈值", result.reasons)

    def test_missing_required_sla_is_unverifiable(self):
        side_effect = evaluate_side_effects(
            snapshot(), snapshot(p95_latency_ms=None), self.thresholds
        )

        self.assertEqual(side_effect.status, "UNVERIFIABLE")

    def test_overlap_prevents_formal_savings(self):
        overlap = find_overlaps(
            (
                ActionScope("ACT-001", "GPU-001", date(2026, 8, 1), date(2026, 8, 31)),
                ActionScope("ACT-002", "GPU-001", date(2026, 8, 15), date(2026, 9, 15)),
            )
        )
        side_effect = evaluate_side_effects(snapshot(), snapshot(), self.thresholds)

        result = finalize_result(benefit(), overlap, side_effect)

        self.assertEqual(result.outcome, "UNVERIFIABLE")
        self.assertEqual(result.realized_savings_usd, 0)
        self.assertIn("行动范围和观察期重叠", result.reasons)


if __name__ == "__main__":
    unittest.main()
