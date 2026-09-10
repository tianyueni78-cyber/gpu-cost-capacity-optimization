from dataclasses import asdict, dataclass
from datetime import date, datetime
import hashlib
import json
from uuid import uuid4


@dataclass(frozen=True)
class MetricSnapshot:
    action_id: str
    resource_pool_ids: tuple[str, ...]
    period_start: date
    period_end: date
    currency: str
    cost_basis: str
    volume_unit: str
    variable_cost_usd: float
    fixed_cost_usd: float
    business_volume: float
    availability_pct: float | None = None
    p95_latency_ms: float | None = None
    queue_time_seconds: float | None = None
    failure_rate_pct: float | None = None
    spare_capacity_pct: float | None = None

    def __post_init__(self):
        if self.period_end < self.period_start:
            raise ValueError("观察期结束日期不能早于开始日期")
        if not self.resource_pool_ids:
            raise ValueError("资源范围不能为空")
        for value in (self.variable_cost_usd, self.fixed_cost_usd, self.business_volume):
            if value < 0:
                raise ValueError("成本和业务量不能小于零")

    @property
    def effective_cost_usd(self) -> float:
        return self.variable_cost_usd + self.fixed_cost_usd


@dataclass(frozen=True)
class BaselineVersion:
    baseline_id: str
    action_id: str
    source_sha256: str
    frozen_at: datetime
    snapshot: MetricSnapshot
    baseline_method: str
    history_is_stable: bool


def _fingerprint(snapshot: MetricSnapshot) -> str:
    payload = asdict(snapshot)
    payload["resource_pool_ids"] = sorted(snapshot.resource_pool_ids)
    text = json.dumps(payload, sort_keys=True, default=lambda value: value.isoformat())
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def freeze_baseline(
    snapshot: MetricSnapshot,
    frozen_at: datetime,
    baseline_method: str = "DIRECT_PERIOD",
    history_is_stable: bool = True,
) -> BaselineVersion:
    if frozen_at.tzinfo is None:
        raise ValueError("基线冻结时间必须包含时区")
    if baseline_method not in {"DIRECT_PERIOD", "HISTORICAL_AVERAGE"}:
        raise ValueError("不支持的基线方法")
    return BaselineVersion(
        baseline_id=str(uuid4()),
        action_id=snapshot.action_id,
        source_sha256=_fingerprint(snapshot),
        frozen_at=frozen_at,
        snapshot=snapshot,
        baseline_method=baseline_method,
        history_is_stable=history_is_stable,
    )
