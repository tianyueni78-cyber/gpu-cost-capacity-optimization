import unittest

import numpy as np
import pandas as pd

from src.models import (
    ModelRejected,
    exponential_smoothing,
    fit_candidate_models,
    seasonal_naive,
    trend_seasonal,
)


def seasonal_series(periods=36):
    index = pd.date_range("2023-01-01", periods=periods, freq="MS")
    season = np.array([90, 92, 95, 100, 105, 110, 115, 112, 108, 103, 98, 94])
    values = np.tile(season, periods // 12) + np.repeat(np.arange(periods // 12) * 5, 12)
    return pd.Series(values.astype(float), index=index)


class ForecastModelsTest(unittest.TestCase):
    def test_each_candidate_returns_ordered_capacity_quantiles(self):
        forecasts = fit_candidate_models(seasonal_series(), horizon=3)
        self.assertEqual(
            {forecast.model_id for forecast in forecasts},
            {"seasonal_naive", "exponential_smoothing", "trend_seasonal"},
        )
        for forecast in forecasts:
            self.assertEqual(len(forecast.point), 3)
            self.assertTrue(np.all(forecast.p50 <= forecast.p90))
            self.assertTrue(np.all(forecast.p90 <= forecast.p99))
            self.assertTrue(np.all(forecast.lower <= forecast.point))
            self.assertTrue(np.all(forecast.point <= forecast.upper))

    def test_seasonal_models_reject_less_than_one_full_season(self):
        short = seasonal_series(36).iloc[:11]
        with self.assertRaisesRegex(ModelRejected, "12个周期"):
            seasonal_naive(short, horizon=3)
        with self.assertRaisesRegex(ModelRejected, "12个周期"):
            trend_seasonal(short, horizon=3)

    def test_exponential_smoothing_is_deterministic_and_uses_explicit_alpha(self):
        series = seasonal_series(24)
        first = exponential_smoothing(series, horizon=2, alpha=0.4)
        second = exponential_smoothing(series, horizon=2, alpha=0.4)
        np.testing.assert_array_equal(first.point, second.point)
        self.assertEqual(first.parameters["alpha"], 0.4)

    def test_trend_seasonal_projects_future_months_without_negative_values(self):
        forecast = trend_seasonal(seasonal_series(), horizon=15)
        self.assertEqual(len(forecast.point), 15)
        self.assertTrue(np.all(forecast.point >= 0))


if __name__ == "__main__":
    unittest.main()
