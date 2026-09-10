from dataclasses import dataclass, replace
from datetime import date

from .benefits import BenefitResult
from .measurement import MetricSnapshot


@dataclass(frozen=True)
class ActionScope:
    action_id: str
    resource_pool_id: str
    period_start: date
    period_end: date

    def __post_init__(self):
        if self.period_end < self.period_start:
            raise ValueError("行动结束日期不能早于开始日期")


@dataclass(frozen=True)
class Overlap:
    action_ids: tuple[str, str]
    resource_pool_id: str


@dataclass(frozen=True)
class SideEffectThresholds:
    min_availability_pct: float
    max_p95_latency_ms: float
    max_queue_time_seconds: float
    max_failure_rate_pct: float
    min_spare_capacity_pct: float


@dataclass(frozen=True)
class SideEffectResult:
    status: str
    violations: tuple[str, ...]


def find_overlaps(scopes: tuple[ActionScope, ...]) -> tuple[Overlap, ...]:
    overlaps = []
    for index, left in enumerate(scopes):
        for right in scopes[index + 1 :]:
            same_resource = left.resource_pool_id == right.resource_pool_id
            intersects = left.period_start <= right.period_end and right.period_start <= left.period_end
            if same_resource and intersects:
                overlaps.append(
                    Overlap(
                        action_ids=(left.action_id, right.action_id),
                        resource_pool_id=left.resource_pool_id,
                    )
                )
    return tuple(overlaps)


def evaluate_side_effects(
    baseline: MetricSnapshot,
    post: MetricSnapshot,
    thresholds: SideEffectThresholds,
) -> SideEffectResult:
    required = (
        post.availability_pct,
        post.p95_latency_ms,
        post.queue_time_seconds,
        post.failure_rate_pct,
        post.spare_capacity_pct,
    )
    if any(value is None for value in required):
        return SideEffectResult("UNVERIFIABLE", ("缺少SLA或安全容量指标",))

    violations = []
    if post.availability_pct < thresholds.min_availability_pct:
        violations.append("可用性低于最低阈值")
    if post.p95_latency_ms > thresholds.max_p95_latency_ms:
        violations.append("P95延迟高于最高阈值")
    if post.queue_time_seconds > thresholds.max_queue_time_seconds:
        violations.append("排队时间高于最高阈值")
    if post.failure_rate_pct > thresholds.max_failure_rate_pct:
        violations.append("失败率高于最高阈值")
    if post.spare_capacity_pct < thresholds.min_spare_capacity_pct:
        violations.append("备用容量低于最低阈值")
    return SideEffectResult("NEGATIVE_IMPACT" if violations else "PASS", tuple(violations))


def finalize_result(
    benefit: BenefitResult,
    overlaps: tuple[Overlap, ...],
    side_effects: SideEffectResult,
) -> BenefitResult:
    involved = any(benefit.action_id in overlap.action_ids for overlap in overlaps)
    if involved:
        return replace(
            benefit,
            realized_savings_usd=0,
            avoided_cost_usd=0,
            evidence_grade="UNVERIFIABLE",
            outcome="UNVERIFIABLE",
            reasons=benefit.reasons + ("行动范围和观察期重叠",),
        )
    if side_effects.status != "PASS":
        return replace(
            benefit,
            evidence_grade="UNVERIFIABLE" if side_effects.status == "UNVERIFIABLE" else benefit.evidence_grade,
            outcome=side_effects.status,
            reasons=benefit.reasons + side_effects.violations,
        )
    return benefit
