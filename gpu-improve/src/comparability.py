from dataclasses import dataclass

from .measurement import BaselineVersion, MetricSnapshot


@dataclass(frozen=True)
class ComparabilityResult:
    allowed: bool
    blocking_reasons: tuple[str, ...]
    warnings: tuple[str, ...]
    evidence_grade: str


def check_comparability(
    baseline: BaselineVersion,
    post: MetricSnapshot,
) -> ComparabilityResult:
    before = baseline.snapshot
    blocking: list[str] = []
    warnings: list[str] = []

    if before.action_id != post.action_id:
        blocking.append("行动编号不一致")
    if set(before.resource_pool_ids) != set(post.resource_pool_ids):
        blocking.append("资源范围不一致")
    if before.currency != post.currency:
        blocking.append("币种不一致")
    if before.cost_basis != post.cost_basis:
        blocking.append("成本口径不一致")
    if before.volume_unit != post.volume_unit:
        blocking.append("业务量单位不一致")

    before_days = (before.period_end - before.period_start).days + 1
    post_days = (post.period_end - post.period_start).days + 1
    if before_days != post_days:
        blocking.append("观察期间长度不一致")
    if post.period_start <= before.period_end:
        blocking.append("行动前后观察期间重叠")

    if baseline.baseline_method == "HISTORICAL_AVERAGE":
        if not baseline.history_is_stable:
            blocking.append("历史平均缺少稳定性证据")
        else:
            warnings.append("使用历史平均基线")

    if blocking:
        return ComparabilityResult(False, tuple(blocking), tuple(warnings), "UNVERIFIABLE")
    grade = "MEDIUM" if warnings else "HIGH"
    return ComparabilityResult(True, (), tuple(warnings), grade)
