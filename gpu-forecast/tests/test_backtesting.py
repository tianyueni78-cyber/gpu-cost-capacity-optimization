import unittest

import numpy as np
import pandas as pd

from src.backtesting import (
    BacktestConfig,
    ForecastOutput,
    rolling_splits,
    run_backtest,
    score_forecast,
)


class BacktestingTest(unittest.TestCase):
    def test_every_training_window_ends_before_test_window(self):
        index = pd.date_range("2024-01-01", periods=24, freq="MS")
        splits = rolling_splits(index, min_train=12, horizon=3)
        self.assertTrue(splits)
        self.assertTrue(all(split.train_end < split.test_start for split in splits))
        self.assertEqual(len(splits), 10)

    def test_unsorted_or_duplicate_index_is_rejected(self):
        unsorted = pd.DatetimeIndex(["2025-02-01", "2025-01-01"])
        duplicate = pd.DatetimeIndex(["2025-01-01", "2025-01-01"])
        with self.assertRaisesRegex(ValueError, "递增且唯一"):
            rolling_splits(unsorted, min_train=1, horizon=1)
        with self.assertRaisesRegex(ValueError, "递增且唯一"):
            rolling_splits(duplicate, min_train=1, horizon=1)

    def test_metrics_include_mae_wape_bias_and_coverage(self):
        metrics = score_forecast([100, 120], [90, 130], [80, 110], [110, 140])
        self.assertEqual(metrics.mae, 10)
        self.assertAlmostEqual(metrics.wape, 20 / 220)
        self.assertEqual(metrics.bias, 0)
        self.assertEqual(metrics.interval_coverage_pct, 100)

    def test_zero_actual_denominator_marks_wape_and_bias_unavailable(self):
        metrics = score_forecast([0, 0], [1, 2], [0, 0], [2, 3])
        self.assertIsNone(metrics.wape)
        self.assertIsNone(metrics.bias)

    def test_backtest_passes_only_past_values_to_model(self):
        series = pd.Series(
            np.arange(1, 19, dtype=float),
            index=pd.date_range("2024-01-01", periods=18, freq="MS"),
        )
        seen_training_ends = []

        def model(train, horizon):
            seen_training_ends.append(train.index[-1])
            point = np.repeat(train.iloc[-1], horizon)
            return ForecastOutput(point=point, lower=point - 1, upper=point + 1)

        result = run_backtest(series, model, BacktestConfig(min_train_periods=12, horizon=3))

        self.assertEqual(len(result.splits), 4)
        self.assertEqual(seen_training_ends, [split.train_end for split in result.splits])
        self.assertTrue(
            all(split.train_end < split.test_start for split in result.splits)
        )
        self.assertEqual(len(result.predictions), 12)
        self.assertIn("actual", result.predictions.columns)


if __name__ == "__main__":
    unittest.main()
