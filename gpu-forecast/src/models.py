from dataclasses import dataclass

import numpy as np
import pandas as pd


class ModelRejected(ValueError):
    """The model cannot be supported by the supplied history."""


@dataclass(frozen=True)
class ModelForecast:
    model_id: str
    point: np.ndarray
    lower: np.ndarray
    upper: np.ndarray
    p50: np.ndarray
    p90: np.ndarray
    p99: np.ndarray
    parameters: dict[str, float | int]


def _validate(series: pd.Series, horizon: int) -> pd.Series:
    if horizon < 1:
        raise ValueError("预测步长必须大于零")
    values = pd.Series(series, dtype=float).dropna()
    if values.empty:
        raise ModelRejected("历史序列为空")
    return values


def _forecast(model_id, point, residuals, parameters) -> ModelForecast:
    point = np.maximum(np.asarray(point, dtype=float), 0)
    residuals = np.abs(np.asarray(residuals, dtype=float))
    residuals = residuals[np.isfinite(residuals)]
    if not residuals.size:
        residuals = np.array([0.0])
    q50, q90, q99 = np.quantile(residuals, [0.50, 0.90, 0.99])
    return ModelForecast(
        model_id=model_id,
        point=point,
        lower=np.maximum(point - q90, 0),
        upper=point + q90,
        p50=point + q50,
        p90=point + q90,
        p99=point + q99,
        parameters=parameters,
    )


def seasonal_naive(series: pd.Series, horizon: int, season_length: int = 12) -> ModelForecast:
    values = _validate(series, horizon)
    if len(values) < season_length:
        raise ModelRejected(f"季节性模型至少需要{season_length}个周期")
    season = values.iloc[-season_length:].to_numpy()
    point = np.resize(season, horizon)
    residuals = (
        values.iloc[season_length:].to_numpy() - values.iloc[:-season_length].to_numpy()
        if len(values) > season_length
        else np.diff(values.to_numpy())
    )
    return _forecast("seasonal_naive", point, residuals, {"season_length": season_length})


def exponential_smoothing(series: pd.Series, horizon: int, alpha: float = 0.3) -> ModelForecast:
    values = _validate(series, horizon)
    if not 0 < alpha <= 1:
        raise ValueError("alpha 必须大于0且不超过1")
    level = float(values.iloc[0])
    fitted = [level]
    for observation in values.iloc[1:]:
        level = alpha * float(observation) + (1 - alpha) * level
        fitted.append(level)
    residuals = values.to_numpy() - np.asarray(fitted)
    return _forecast(
        "exponential_smoothing",
        np.repeat(level, horizon),
        residuals,
        {"alpha": alpha},
    )


def _design(index: pd.DatetimeIndex, positions: np.ndarray) -> np.ndarray:
    month = index.month.to_numpy()
    dummies = np.column_stack([(month == value).astype(float) for value in range(2, 13)])
    return np.column_stack([np.ones(len(index)), positions, dummies])


def trend_seasonal(series: pd.Series, horizon: int, season_length: int = 12) -> ModelForecast:
    values = _validate(series, horizon)
    if len(values) < season_length:
        raise ModelRejected(f"趋势季节模型至少需要{season_length}个周期")
    if not isinstance(values.index, pd.DatetimeIndex):
        raise ValueError("趋势季节模型必须使用时间索引")
    train_positions = np.arange(len(values), dtype=float)
    train_design = _design(values.index, train_positions)
    coefficients, *_ = np.linalg.lstsq(train_design, values.to_numpy(), rcond=None)
    fitted = train_design @ coefficients
    future_index = pd.date_range(
        values.index[-1] + pd.offsets.MonthBegin(1), periods=horizon, freq="MS"
    )
    future_positions = np.arange(len(values), len(values) + horizon, dtype=float)
    point = _design(future_index, future_positions) @ coefficients
    return _forecast(
        "trend_seasonal",
        point,
        values.to_numpy() - fitted,
        {"season_length": season_length},
    )


def fit_candidate_models(series: pd.Series, horizon: int) -> tuple[ModelForecast, ...]:
    return (
        seasonal_naive(series, horizon),
        exponential_smoothing(series, horizon),
        trend_seasonal(series, horizon),
    )
