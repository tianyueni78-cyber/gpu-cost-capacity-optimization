from dataclasses import dataclass

from .comparability import ComparabilityResult
from .measurement import BaselineVersion, MetricSnapshot
from .models import ActionRecord, ActionType


@dataclass(frozen=True)
class BenefitResult:
    action_id: str
    method_id: str
    formula_version: str
    counterfactual_cost_usd: float
    actual_cost_usd: float
    implementation_cost_usd: float
    realized_savings_usd: float
    avoided_cost_usd: float
    evidence_grade: str
    outcome: str
    reasons: tuple[str, ...]


def _unverifiable(action: ActionRecord, reasons: tuple[str, ...]) -> BenefitResult:
    return BenefitResult(
        action_id=action.action_id,
        method_id="UNVERIFIABLE",
        formula_version="1.0",
        counterfactual_cost_usd=0,
        actual_cost_usd=0,
        implementation_cost_usd=action.implementation_cost_usd,
        realized_savings_usd=0,
        avoided_cost_usd=0,
        evidence_grade="UNVERIFIABLE",
        outcome="UNVERIFIABLE",
        reasons=reasons,
    )


def _normalized_counterfactual(before: MetricSnapshot, after: MetricSnapshot) -> float:
    if before.business_volume <= 0:
        raise ValueError("基线业务量必须大于零")
    variable = before.variable_cost_usd / before.business_volume * after.business_volume
    return variable + before.fixed_cost_usd


def verify_benefit(
    action: ActionRecord,
    baseline: BaselineVersion,
    post: MetricSnapshot,
    comparability: ComparabilityResult,
) -> BenefitResult:
    if not comparability.allowed:
        return _unverifiable(action, comparability.blocking_reasons)

    before = baseline.snapshot
    actual = post.effective_cost_usd
    avoided = 0.0

    if action.action_type == ActionType.RATE_COMMITMENT:
        if post.on_demand_equivalent_cost_usd is None:
            return _unverifiable(action, ("缺少按需等价成本",))
        method = "ON_DEMAND_EQUIVALENT"
        counterfactual = post.on_demand_equivalent_cost_usd
    elif action.action_type == ActionType.GPU_MIGRATION:
        if before.throughput_per_second is None or post.throughput_per_second is None:
            return _unverifiable(action, ("型号替换缺少性能证据",))
        if post.throughput_per_second < before.throughput_per_second * 0.95:
            return _unverifiable(action, ("型号替换性能不可比",))
        method = "COMPARABLE_WORKLOAD_AND_PERFORMANCE"
        counterfactual = _normalized_counterfactual(before, post)
    elif action.action_type == ActionType.SCHEDULING:
        operational = (post.p95_latency_ms, post.queue_time_seconds, post.failure_rate_pct)
        if any(value is None for value in operational):
            return _unverifiable(action, ("流程优化缺少运营指标",))
        method = "UNIT_COST_AND_OPERATIONS"
        counterfactual = _normalized_counterfactual(before, post)
    elif action.action_type == ActionType.AVOIDED_PURCHASE:
        if before.planned_purchase_cost_usd is None or post.planned_purchase_cost_usd is None:
            return _unverifiable(action, ("缺少已批准采购基线",))
        method = "APPROVED_PURCHASE_BASELINE"
        counterfactual = before.planned_purchase_cost_usd
        actual = post.planned_purchase_cost_usd
        avoided = max(0.0, counterfactual - actual)
    else:
        method = "UNIT_COST_NORMALIZED"
        counterfactual = _normalized_counterfactual(before, post)

    realized = 0.0 if action.action_type == ActionType.AVOIDED_PURCHASE else max(
        0.0, counterfactual - actual - action.implementation_cost_usd
    )
    outcome = "VERIFIED" if realized > 0 or avoided > 0 else "NOT_REALIZED"
    return BenefitResult(
        action_id=action.action_id,
        method_id=method,
        formula_version="1.0",
        counterfactual_cost_usd=round(counterfactual, 2),
        actual_cost_usd=round(actual, 2),
        implementation_cost_usd=action.implementation_cost_usd,
        realized_savings_usd=round(realized, 2),
        avoided_cost_usd=round(avoided, 2),
        evidence_grade=comparability.evidence_grade,
        outcome=outcome,
        reasons=(),
    )
