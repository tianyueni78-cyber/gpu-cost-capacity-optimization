import unittest

from src.demo import run_demo_portfolio
from src.reporting import build_ledger, export_csv_bytes


class EndToEndTest(unittest.TestCase):
    def test_demo_portfolio_contains_three_evidence_outcomes(self):
        results = run_demo_portfolio()

        self.assertEqual(
            {result.outcome for result in results},
            {"VERIFIED", "NEGATIVE_IMPACT", "UNVERIFIABLE"},
        )
        self.assertGreater(len(export_csv_bytes(build_ledger(list(results)))), 100)


if __name__ == "__main__":
    unittest.main()
