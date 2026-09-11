import hashlib
from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import uuid4

import pandas as pd


GRAIN = ("period", "team_id", "workload_type", "gpu_model", "region")
REQUIRED_FORECAST_COLUMNS = {*GRAIN, "system_forecast"}


@dataclass(frozen=True)
class ForecastAdjustment:
    period: str
    team_id: str
    workload_type: str
    gpu_model: str
    region: str
    adjustment_type: str
    delta: float
    confirmed: bool
    reason: str

    @property
    def grain(self) -> tuple[str, ...]:
        return (
            _period(self.period), self.team_id, self.workload_type,
            self.gpu_model, self.region,
        )


@dataclass(frozen=True)
class PublishedForecast:
    system: float
    event_delta: float
    manual_delta: float
    published: float


@dataclass(frozen=True)
class ForecastPoint:
    period: str
    team_id: str
    workload_type: str
    gpu_model: str
    region: str
    system: float
    event_delta: float
    manual_delta: float
    published: float


@dataclass(frozen=True)
class ForecastVersion:
    version_id: str
    data_sha256: str
    training_cutoff: str
    model_version: str
    evidence_grade: str
    actor: str
    published_at: datetime
    reason: str
    points: tuple[ForecastPoint, ...]
    adjustments: tuple[ForecastAdjustment, ...]


def _period(value) -> str:
    return pd.Timestamp(value).strftime("%Y-%m-%d")


def apply_adjustments(
    system: float,
    event_delta: float = 0,
    manual_delta: float = 0,
) -> PublishedForecast:
    return PublishedForecast(
        float(system),
        float(event_delta),
        float(manual_delta),
        float(system) + float(event_delta) + float(manual_delta),
    )


def _validate_adjustments(adjustments: tuple[ForecastAdjustment, ...]) -> None:
    for adjustment in adjustments:
        kind = adjustment.adjustment_type.upper()
        if kind not in {"EVENT", "MANUAL"}:
            raise ValueError(f"不支持的调整类型: {adjustment.adjustment_type}")
        if kind == "EVENT" and not adjustment.confirmed:
            raise ValueError("业务事件尚未确认，不能进入正式发布")
        if kind == "MANUAL" and not adjustment.reason.strip():
            raise ValueError("人工调整必须填写原因")


def publish_forecast(
    system_forecast: pd.DataFrame,
    adjustments: tuple[ForecastAdjustment, ...],
    *,
    actor: str,
    reason: str,
    data_snapshot: str | bytes,
    training_cutoff: str,
    model_version: str,
    evidence_grade: str,
    published_at: datetime | None = None,
) -> ForecastVersion:
    missing = REQUIRED_FORECAST_COLUMNS - set(system_forecast.columns)
    if missing:
        raise ValueError(f"系统预测缺少字段: {', '.join(sorted(missing))}")
    if system_forecast.duplicated(list(GRAIN)).any():
        raise ValueError("系统预测粒度重复")
    if not actor.strip() or not reason.strip():
        raise ValueError("发布人和发布原因不能为空")
    _validate_adjustments(adjustments)

    adjustment_by_grain: dict[tuple[str, ...], list[ForecastAdjustment]] = {}
    for adjustment in adjustments:
        adjustment_by_grain.setdefault(adjustment.grain, []).append(adjustment)

    points = []
    known_grains = set()
    for row in system_forecast.itertuples(index=False):
        grain = (
            _period(row.period), row.team_id, row.workload_type, row.gpu_model, row.region,
        )
        known_grains.add(grain)
        scoped = adjustment_by_grain.get(grain, [])
        event_delta = sum(item.delta for item in scoped if item.adjustment_type.upper() == "EVENT")
        manual_delta = sum(item.delta for item in scoped if item.adjustment_type.upper() == "MANUAL")
        value = apply_adjustments(row.system_forecast, event_delta, manual_delta)
        points.append(ForecastPoint(*grain, value.system, value.event_delta, value.manual_delta, value.published))

    unknown = set(adjustment_by_grain) - known_grains
    if unknown:
        raise ValueError("调整范围在系统预测中不存在")

    snapshot_bytes = data_snapshot if isinstance(data_snapshot, bytes) else data_snapshot.encode("utf-8")
    timestamp = published_at or datetime.now(timezone.utc)
    if timestamp.tzinfo is None:
        raise ValueError("发布时间必须包含时区")
    return ForecastVersion(
        version_id=f"FV-{uuid4()}",
        data_sha256=hashlib.sha256(snapshot_bytes).hexdigest(),
        training_cutoff=_period(training_cutoff),
        model_version=model_version,
        evidence_grade=evidence_grade,
        actor=actor,
        published_at=timestamp,
        reason=reason,
        points=tuple(points),
        adjustments=tuple(adjustments),
    )
