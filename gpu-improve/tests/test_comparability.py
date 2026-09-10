from dataclasses import replace
from datetime import date, datetime, timezone
import unittest

from src.comparability import check_comparability
from src.measurement import MetricSnapshot, freeze_baseline


def snapshot(**changes):
    base = MetricSnapshot(
        action_id="ACT-001",
        resource_pool_ids=("GPU-001",),
        period_start=date(2026, 7, 1),
        period_end=date(2026, 7, 31),
        currency="USD",
        cost_basis="EFFECTIVE_COST",
        volume_unit="requests",
        variable_cost_usd=8000,
        fixed_cost_usd=2000,
        business_volume=1000,
        availability_pct=99.95,
        p95_latency_ms=180,
        queue_time_seconds=4,
        failure_rate_pct=0.2,
        spare_capacity_pct=20,
    )
    return replace(base, **changes)


class BaselineTest(unittest.TestCase):
    def test_freeze_creates_stable_fingerprint_and_new_version_id(self):
        first = freeze_baseline(
            snapshot(),
            frozen_at=datetime(2026, 8, 1, tzinfo=timezone.utc),
        )
        second = freeze_baseline(
            snapshot(),
            frozen_at=datetime(2026, 8, 2, tzinfo=timezone.utc),
        )

        self.assertEqual(first.source_sha256, second.source_sha256)
        self.assertNotEqual(first.baseline_id, second.baseline_id)


class ComparabilityTest(unittest.TestCase):
    def setUp(self):
        self.baseline = freeze_baseline(
            snapshot(),
            frozen_at=datetime(2026, 8, 1, tzinfo=timezone.utc),
        )
        self.post = snapshot(
            period_start=date(2026, 9, 1),
            period_end=date(2026, 10, 1),
        )

    def test_matching_snapshots_are_high_evidence(self):
        result = check_comparability(self.baseline, self.post)

        self.assertTrue(result.allowed)
        self.assertEqual(result.evidence_grade, "HIGH")
        self.assertEqual(result.blocking_reasons, ())

    def test_currency_mismatch_blocks_verification(self):
        result = check_comparability(self.baseline, replace(self.post, currency="CNY"))

        self.assertFalse(result.allowed)
        self.assertIn("币种不一致", result.blocking_reasons)
        self.assertEqual(result.evidence_grade, "UNVERIFIABLE")

    def test_scope_and_business_unit_mismatch_are_both_reported(self):
        result = check_comparability(
            self.baseline,
            replace(self.post, resource_pool_ids=("GPU-002",), volume_unit="jobs"),
        )

        self.assertIn("资源范围不一致", result.blocking_reasons)
        self.assertIn("业务量单位不一致", result.blocking_reasons)

    def test_unstable_historical_average_is_not_accepted(self):
        baseline = freeze_baseline(
            snapshot(),
            frozen_at=datetime(2026, 8, 1, tzinfo=timezone.utc),
            baseline_method="HISTORICAL_AVERAGE",
            history_is_stable=False,
        )

        result = check_comparability(baseline, self.post)

        self.assertFalse(result.allowed)
        self.assertIn("历史平均缺少稳定性证据", result.blocking_reasons)

    def test_stable_historical_average_is_medium_evidence(self):
        baseline = freeze_baseline(
            snapshot(),
            frozen_at=datetime(2026, 8, 1, tzinfo=timezone.utc),
            baseline_method="HISTORICAL_AVERAGE",
            history_is_stable=True,
        )

        result = check_comparability(baseline, self.post)

        self.assertTrue(result.allowed)
        self.assertEqual(result.evidence_grade, "MEDIUM")
        self.assertIn("使用历史平均基线", result.warnings)


if __name__ == "__main__":
    unittest.main()
