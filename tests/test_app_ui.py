import unittest
from pathlib import Path


class AppUiContractTest(unittest.TestCase):
    def test_only_completed_capacity_pages_are_exposed(self):
        source = Path("app.py").read_text(encoding="utf-8")

        for page in ("基线接入", "目标与约束", "容量优化", "方案与审批"):
            self.assertIn(page, source)
        self.assertNotIn('"运行配置优化"', source)
        self.assertNotIn('"采购组合优化"', source)


if __name__ == "__main__":
    unittest.main()
