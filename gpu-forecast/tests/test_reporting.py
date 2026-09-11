import unittest

import pandas as pd

from src.reporting import can_publish_purchase_plan, dataframe_csv, management_summary


class ReportingTest(unittest.TestCase):
    def test_csv_uses_utf8_bom(self):
        self.assertTrue(dataframe_csv(pd.DataFrame([{"团队": "搜索"}])).startswith(b"\xef\xbb\xbf"))

    def test_unverifiable_scope_cannot_publish_purchase_plan(self):
        self.assertFalse(can_publish_purchase_plan("UNVERIFIABLE"))

    def test_summary_contains_decision_evidence(self):
        text = management_summary("P90", 5.2, 3, 6000, "交付周期")
        for item in ("P90", "5.2", "3", "6000", "交付周期"):
            self.assertIn(item, text)

