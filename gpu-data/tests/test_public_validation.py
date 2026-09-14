import json
import tempfile
import unittest
from pathlib import Path

import pandas as pd

from src.public_validation import prepare_validation_cases


SOURCE = Path(__file__).parents[1] / "validation" / "alibaba_t4" / "source"


class PublicValidationTest(unittest.TestCase):
    def test_real_alibaba_slice_matches_independent_benchmark(self):
        with tempfile.TemporaryDirectory() as folder:
            cases = prepare_validation_cases(SOURCE, Path(folder))
            normal = cases["normal"]
            inventory = pd.read_csv(normal / "inventory.csv")
            usage = pd.read_csv(normal / "usage.csv")
            billing = pd.read_csv(normal / "billing.csv")
            benchmark = json.loads((normal / "benchmark.json").read_text(encoding="utf-8"))

            self.assertEqual(len(inventory), 8)
            self.assertEqual(inventory["gpu_count"].sum(), 20)
            self.assertAlmostEqual(billing["billed_gpu_hours"].sum(), 2590.025833333333, places=9)
            self.assertAlmostEqual(billing["net_cost_usd"].sum(), 1362.3535883333334, places=9)
            self.assertAlmostEqual(usage["gpu_utilization_pct"].median(), 2.6458597815259455, places=9)
            self.assertAlmostEqual(usage["gpu_utilization_pct"].quantile(.95), 84.97296515627833, places=9)
            self.assertEqual(benchmark["price_evidence"], "Azure public Linux on-demand retail comparator")
            self.assertEqual(benchmark["source_gpu_utilization"], "Alibaba PAI observed lifetime average")

    def test_fault_cases_block_required_fields_without_turning_missing_telemetry_into_zero(self):
        with tempfile.TemporaryDirectory() as folder:
            cases = prepare_validation_cases(SOURCE, Path(folder))
            blocked_inventory = pd.read_csv(cases["blocked"] / "inventory.csv")
            missing_usage = pd.read_csv(cases["missing_telemetry"] / "usage.csv")

            self.assertNotIn("gpu_model", blocked_inventory.columns)
            self.assertTrue(missing_usage["gpu_utilization_pct"].isna().any())
            self.assertEqual(
                missing_usage.loc[missing_usage["gpu_utilization_pct"].isna(), "telemetry_status"].unique().tolist(),
                ["missing"],
            )


if __name__ == "__main__":
    unittest.main()
