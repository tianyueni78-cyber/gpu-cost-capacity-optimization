import unittest

from src.backtesting import ForecastMetrics
from src.selection import CandidateBacktest, select_model


class ModelSelectionTest(unittest.TestCase):
    def test_selects_lowest_weighted_decision_loss(self):
        candidates = (
            CandidateBacktest(
                "seasonal_naive",
                ForecastMetrics(mae=8, wape=0.08, bias=-0.02, interval_coverage_pct=90),
            ),
            CandidateBacktest(
                "trend_seasonal",
                ForecastMetrics(mae=7, wape=0.07, bias=-0.08, interval_coverage_pct=90),
            ),
        )
        chosen = select_model(candidates, {"wape": 1, "under_bias": 2})
        self.assertEqual(chosen.model_id, "seasonal_naive")
        self.assertEqual(len(chosen.scores), 2)

    def test_rejected_and_unscorable_candidates_are_preserved_as_evidence(self):
        candidates = (
            CandidateBacktest("seasonal_naive", None, "历史不足一个季节"),
            CandidateBacktest(
                "exponential_smoothing",
                ForecastMetrics(mae=2, wape=None, bias=None, interval_coverage_pct=100),
            ),
        )
        result = select_model(candidates, {"mae": 1})
        self.assertEqual(result.model_id, "exponential_smoothing")
        rejected = next(score for score in result.scores if score.model_id == "seasonal_naive")
        self.assertEqual(rejected.rejection_reason, "历史不足一个季节")

    def test_raises_when_no_candidate_can_be_scored(self):
        with self.assertRaisesRegex(ValueError, "没有可选择的模型"):
            select_model((CandidateBacktest("seasonal_naive", None, "历史不足"),), {"wape": 1})


if __name__ == "__main__":
    unittest.main()
