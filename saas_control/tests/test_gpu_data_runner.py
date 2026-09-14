import tempfile
import unittest
from pathlib import Path

from saas_control.app.gpu_data_runner import run_analysis


ROOT = Path(__file__).parents[2]
TEMP_ROOT = ROOT / ".tmp"
TEMP_ROOT.mkdir(exist_ok=True)


class GpuDataRunnerTest(unittest.TestCase):
    def test_sample_runs_real_modules_and_writes_four_artifacts(self):
        with tempfile.TemporaryDirectory(dir=TEMP_ROOT) as output:
            result = run_analysis(ROOT / "gpu-data" / "sample_data", Path(output))
            self.assertEqual(result["status"], "SUCCEEDED")
            self.assertEqual(result["summary"]["total_cost_usd"], 1100.0)
            self.assertEqual(result["summary"]["gpu_count"], 12.0)
            self.assertGreater(result["summary"]["idle_candidate_count"], 0)
            self.assertEqual(
                {"report.md", "idle_candidates.csv", "data_quality.csv", "cost_allocation.csv"},
                {Path(item["path"]).name for item in result["artifacts"]},
            )
            for item in result["artifacts"]:
                self.assertGreater(Path(item["path"]).stat().st_size, 0)

    def test_blocking_audit_does_not_publish_formal_analysis(self):
        with tempfile.TemporaryDirectory(dir=TEMP_ROOT) as source, tempfile.TemporaryDirectory(dir=TEMP_ROOT) as output:
            source_path = Path(source)
            for name in ("inventory", "usage", "billing", "sla"):
                content = (ROOT / "gpu-data" / "sample_data" / f"{name}.csv").read_bytes()
                (source_path / f"{name}.csv").write_bytes(content)
            (source_path / "inventory.csv").write_text("resource_pool_id,team_id\nPOOL-X,TEAM-X\n", encoding="utf-8")
            result = run_analysis(source_path, Path(output))
            self.assertEqual(result["status"], "BLOCKED")
            self.assertGreater(result["summary"]["blocking_count"], 0)
            self.assertNotIn("total_cost_usd", result["summary"])


if __name__ == "__main__":
    unittest.main()
