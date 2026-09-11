from collections.abc import Callable, Sequence
from dataclasses import dataclass

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class TimeSplit:
    train_positions: tuple[int, ...]
    test_positions: tuple[int, ...]
    train_start: pd.Timestamp
    train_end: pd.Timestamp
    test_start: pd.Timestamp
    test_end: pd.Timestamp


@dataclass(frozen=True)
class ForecastOutput:
    point: Sequence[float]
    lower: Sequence[float]
    upper: Sequence[float]


@dataclass(frozen=True)
class ForecastMetrics:
    mae: float
    wape: float | None
    bias: float | None
    interval_coverage_pct: float


@dataclass(frozen=True)
class BacktestConfig:
    min_train_periods: int = 12
    horizon: int = 3
    step: int = 1


@dataclass(frozen=True)
class BacktestResult:
    splits: tuple[TimeSplit, ...]
    predictions: pd.DataFrame
    metrics: ForecastMetrics


def rolling_splits(
    index: pd.DatetimeIndex,
    min_train: int,
    horizon: int,
    step: int = 1,
) -> tuple[TimeSplit, ...]:
    index = pd.DatetimeIndex(index)
    if not index.is_monotonic_increasing or not index.is_unique:
        raise ValueError("时间索引必须递增且唯一")
    if min_train < 1 or horizon < 1 or step < 1:
        raise ValueError("训练窗口、预测步长和移动步长必须大于零")

    splits = []
    for test_start in range(min_train, len(index) - horizon + 1, step):
        train_positions = tuple(range(test_start))
        test_positions = tuple(range(test_start, test_start + horizon))
        splits.append(
            TimeSplit(
                train_positions=train_positions,
                test_positions=test_positions,
                train_start=index[0],
                train_end=index[test_start - 1],
                test_start=index[test_start],
                test_end=index[test_start + horizon - 1],
            )
        )
    return tuple(splits)


def score_forecast(actual, predicted, lower, upper) -> ForecastMetrics:
    actual_values = np.asarray(actual, dtype=float)
    predicted_values = np.asarray(predicted, dtype=float)
    lower_values = np.asarray(lower, dtype=float)
    upper_values = np.asarray(upper, dtype=float)
    lengths = {len(actual_values), len(predicted_values), len(lower_values), len(upper_values)}
    if len(lengths) != 1 or not actual_values.size:
        raise ValueError("实际值、预测值和区间必须非空且长度一致")

    absolute_error = np.abs(actual_values - predicted_values)
    denominator = float(np.abs(actual_values).sum())
    wape = float(absolute_error.sum() / denominator) if denominator else None
    bias = float((predicted_values - actual_values).sum() / denominator) if denominator else None
    coverage = float(
        100 * np.mean((actual_values >= lower_values) & (actual_values <= upper_values))
    )
    return ForecastMetrics(float(absolute_error.mean()), wape, bias, coverage)


def run_backtest(
    series: pd.Series,
    model: Callable[[pd.Series, int], ForecastOutput],
    config: BacktestConfig,
) -> BacktestResult:
    if not isinstance(series.index, pd.DatetimeIndex):
        raise ValueError("回测序列必须使用时间索引")
    splits = rolling_splits(
        series.index,
        config.min_train_periods,
        config.horizon,
        config.step,
    )
    if not splits:
        raise ValueError("历史长度不足以生成滚动回测窗口")

    rows = []
    for split_number, split in enumerate(splits, start=1):
        train = series.iloc[list(split.train_positions)].copy()
        test = series.iloc[list(split.test_positions)]
        forecast = model(train, len(test))
        arrays = [
            np.asarray(forecast.point, dtype=float),
            np.asarray(forecast.lower, dtype=float),
            np.asarray(forecast.upper, dtype=float),
        ]
        if any(len(values) != len(test) for values in arrays):
            raise ValueError("模型输出长度必须等于测试窗口长度")
        for position, timestamp in enumerate(test.index):
            rows.append(
                {
                    "split_number": split_number,
                    "period": timestamp,
                    "train_end": split.train_end,
                    "actual": float(test.iloc[position]),
                    "predicted": float(arrays[0][position]),
                    "lower": float(arrays[1][position]),
                    "upper": float(arrays[2][position]),
                }
            )

    predictions = pd.DataFrame(rows)
    metrics = score_forecast(
        predictions["actual"],
        predictions["predicted"],
        predictions["lower"],
        predictions["upper"],
    )
    return BacktestResult(splits, predictions, metrics)
