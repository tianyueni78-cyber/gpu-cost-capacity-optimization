from dataclasses import dataclass
from typing import Mapping

from .backtesting import ForecastMetrics


@dataclass(frozen=True)
class CandidateBacktest:
    model_id: str
    metrics: ForecastMetrics | None
    rejection_reason: str | None = None


@dataclass(frozen=True)
class ModelScore:
    model_id: str
    decision_loss: float | None
    rejection_reason: str | None


@dataclass(frozen=True)
class SelectionResult:
    model_id: str
    decision_loss: float
    scores: tuple[ModelScore, ...]


def _metric_value(metrics: ForecastMetrics, name: str) -> float | None:
    if name == "mae":
        return metrics.mae
    if name == "wape":
        return metrics.wape
    if name == "under_bias":
        return None if metrics.bias is None else max(0.0, -metrics.bias)
    if name == "coverage_gap":
        return abs(90.0 - metrics.interval_coverage_pct) / 100
    raise ValueError(f"不支持的模型损失项: {name}")


def select_model(
    backtests: tuple[CandidateBacktest, ...],
    loss_weights: Mapping[str, float],
) -> SelectionResult:
    if not loss_weights:
        raise ValueError("至少配置一个模型损失权重")
    scores = []
    for candidate in backtests:
        reason = candidate.rejection_reason
        loss = None
        if candidate.metrics is not None and reason is None:
            values = [_metric_value(candidate.metrics, name) for name in loss_weights]
            if all(value is not None for value in values):
                loss = sum(
                    float(loss_weights[name]) * float(value)
                    for name, value in zip(loss_weights, values)
                )
            else:
                reason = "所选损失指标不可计算"
        elif reason is None:
            reason = "缺少回测指标"
        scores.append(ModelScore(candidate.model_id, loss, reason))

    eligible = [score for score in scores if score.decision_loss is not None]
    if not eligible:
        raise ValueError("没有可选择的模型")
    chosen = min(eligible, key=lambda score: (score.decision_loss, score.model_id))
    return SelectionResult(chosen.model_id, float(chosen.decision_loss), tuple(scores))
