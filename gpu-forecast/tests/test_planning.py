import dataclasses
import unittest
from datetime import datetime, timezone

import pandas as pd

from src.planning import (
    ForecastAdjustment,
    apply_adjustments,
    publish_forecast,
)


def system_forecast():
    return pd.DataFrame(
        {
            "period": ["2026-01-01", "2026-02-01"],
            "team_id": ["TEAM-A", "TEAM-A"],
            "workload_type": ["Inference", "Inference"],
            "gpu_model": ["H100-80GB", "H100-80GB"],
            "region": ["cn-east-1", "cn-east-1"],
            "system_forecast": [100.0, 110.0],
        }
    )


class PlanningTest(unittest.TestCase):
    def test_published_value_keeps_system_event_and_manual_layers(self):
        value = apply_adjustments(system=100, event_delta=20, manual_delta=-5)
        self.assertEqual(value.published, 115)
        self.assertEqual((value.system, value.event_delta, value.manual_delta), (100, 20, -5))

    def test_unconfirmed_event_cannot_enter_published_forecast(self):
        adjustment = ForecastAdjustment(
            period="2026-01-01",
            team_id="TEAM-A",
            workload_type="Inference",
            gpu_model="H100-80GB",
            region="cn-east-1",
            adjustment_type="EVENT",
            delta=20,
            confirmed=False,
            reason="待确认客户上线",
        )
        with self.assertRaisesRegex(ValueError, "业务事件尚未确认"):
            publish_forecast(system_forecast(), (adjustment,), **metadata())

    def test_manual_adjustment_requires_reason(self):
        adjustment = ForecastAdjustment(
            period="2026-01-01",
            team_id="TEAM-A",
            workload_type="Inference",
            gpu_model="H100-80GB",
            region="cn-east-1",
            adjustment_type="MANUAL",
            delta=-5,
            confirmed=True,
            reason="",
        )
        with self.assertRaisesRegex(ValueError, "人工调整必须填写原因"):
            publish_forecast(system_forecast(), (adjustment,), **metadata())

    def test_publish_preserves_layers_fingerprint_and_metadata(self):
        adjustments = (
            ForecastAdjustment(
                "2026-01-01", "TEAM-A", "Inference", "H100-80GB", "cn-east-1",
                "EVENT", 20, True, "已确认客户上线",
            ),
            ForecastAdjustment(
                "2026-01-01", "TEAM-A", "Inference", "H100-80GB", "cn-east-1",
                "MANUAL", -5, True, "扣除一次性压测",
            ),
        )
        version = publish_forecast(system_forecast(), adjustments, **metadata())
        first = version.points[0]
        self.assertEqual((first.system, first.event_delta, first.manual_delta, first.published), (100, 20, -5, 115))
        self.assertEqual(len(version.data_sha256), 64)
        self.assertEqual(version.actor, "USER-1")
        self.assertEqual(version.training_cutoff, "2025-12-01")

    def test_republish_creates_new_immutable_version(self):
        first = publish_forecast(system_forecast(), (), **metadata())
        second = publish_forecast(system_forecast(), (), **metadata(reason="客户签约更新"))
        self.assertNotEqual(first.version_id, second.version_id)
        self.assertEqual(first.points[0].published, 100)
        with self.assertRaises(dataclasses.FrozenInstanceError):
            first.reason = "覆盖旧原因"


def metadata(reason="季度容量计划"):
    return {
        "actor": "USER-1",
        "reason": reason,
        "data_snapshot": "snapshot-v1",
        "training_cutoff": "2025-12-01",
        "model_version": "trend_seasonal-v1",
        "evidence_grade": "HIGH",
        "published_at": datetime(2026, 1, 2, tzinfo=timezone.utc),
    }


if __name__ == "__main__":
    unittest.main()
