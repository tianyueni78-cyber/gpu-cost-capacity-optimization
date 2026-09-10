from dataclasses import replace
from datetime import date, datetime, timezone

from .benefits import verify_benefit
from .comparability import check_comparability
from .guards import SideEffectThresholds, evaluate_side_effects, finalize_result
from .measurement import MetricSnapshot, freeze_baseline
from .models import ActionRecord, ActionType


THRESHOLDS = SideEffectThresholds(99.9, 200, 5, 0.5, 10)


def _action(action_id: str) -> ActionRecord:
    return ActionRecord(
        action_id=action_id,
        action_type=ActionType.RIGHTSIZE,
        resource_pool_id="GPU-001",
        owner="finops@example.com",
        approved_at=date(2026, 8, 1),
        planned_execution_at=date(2026, 8, 15),
        estimated_savings_usd=1200,
        implementation_cost_usd=100,
    )


def _before(action_id: str) -> MetricSnapshot:
    return MetricSnapshot(
        action_id=action_id,
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


def _post(before: MetricSnapshot) -> MetricSnapshot:
    return replace(
        before,
        period_start=date(2026, 9, 1),
        period_end=date(2026, 10, 1),
        variable_cost_usd=7000,
    )


def _evaluate(action_id: str, post_changes=None):
    action = _action(action_id)
    before = _before(action_id)
    post = replace(_post(before), **(post_changes or {}))
    baseline = freeze_baseline(before, datetime(2026, 8, 1, tzinfo=timezone.utc))
    comparability = check_comparability(baseline, post)
    raw = verify_benefit(action, baseline, post, comparability)
    side_effects = evaluate_side_effects(before, post, THRESHOLDS)
    return finalize_result(raw, (), side_effects)


def run_demo_portfolio():
    verified = _evaluate("ACT-VERIFIED")
    negative = _evaluate("ACT-NEGATIVE", {"availability_pct": 99.5})
    unverifiable = _evaluate("ACT-UNVERIFIABLE", {"currency": "CNY"})
    return verified, negative, unverifiable
