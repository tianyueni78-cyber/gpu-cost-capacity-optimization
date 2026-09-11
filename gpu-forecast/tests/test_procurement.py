import unittest
from datetime import date

import pandas as pd

from src.procurement import build_purchase_plan


class ProcurementTest(unittest.TestCase):
    def _scenarios(self, grade="HIGH"):
        return pd.DataFrame([{
            "period": "2027-03-01", "team_id": "A", "workload_type": "Inference",
            "gpu_model": "H100", "region": "east", "percentile": "P90",
            "shortfall_gpu_count": 2, "evidence_grade": grade, "quota_gpu_count": 1,
        }])

    def _rules(self):
        return pd.DataFrame([{
            "gpu_model": "H100", "region": "east", "procurement_method": "OnDemand",
            "effective_rate": 1000, "billing_periods": 3, "lead_days": 30,
            "valid_from": "2026-01-01", "valid_to": "2027-12-31",
        }])

    def test_latest_decision_date_includes_lead_time_and_approval_buffer(self):
        plan = build_purchase_plan(self._scenarios(), self._rules(), 7)
        self.assertEqual(plan.rows.iloc[0]["latest_decision_date"], date(2027, 1, 23))

    def test_low_evidence_produces_observation_not_purchase_commitment(self):
        plan = build_purchase_plan(self._scenarios("LOW"), self._rules(), 7)
        self.assertEqual(plan.rows.iloc[0]["recommendation_status"], "OBSERVATION_ONLY")

    def test_budget_is_reproducible_and_quota_risk_is_visible(self):
        row = build_purchase_plan(self._scenarios(), self._rules(), 7).rows.iloc[0]
        self.assertEqual(row["budget"], 6000)
        self.assertIn("配额", row["risks"])

    def test_expired_price_blocks_formal_budget(self):
        rules = self._rules()
        rules.loc[0, "valid_to"] = "2026-12-31"
        row = build_purchase_plan(self._scenarios(), rules, 7).rows.iloc[0]
        self.assertEqual(row["recommendation_status"], "BLOCKED")
        self.assertTrue(pd.isna(row["budget"]))


if __name__ == "__main__":
    unittest.main()
