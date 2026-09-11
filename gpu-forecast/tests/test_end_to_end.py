import unittest

from src.demo import run_demo_portfolio


class EndToEndTest(unittest.TestCase):
    def test_demo_contains_publish_observe_and_block_outcomes(self):
        portfolio = run_demo_portfolio()
        self.assertEqual(set(portfolio["decision_status"]), {"PUBLISHABLE", "OBSERVATION_ONLY", "UNVERIFIABLE"})
        self.assertEqual(portfolio["planned_gpu_count"].sum(), portfolio.attrs["total_planned_gpu_count"])


if __name__ == "__main__":
    unittest.main()
