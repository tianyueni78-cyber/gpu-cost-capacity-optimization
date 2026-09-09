import unittest
from pathlib import Path


class AppUiContractTest(unittest.TestCase):
    def test_only_completed_capacity_pages_are_exposed(self):
        source = Path("app.py").read_text(encoding="utf-8")

        for page in ("基线接入", "目标与约束", "容量优化", "方案与审批"):
            self.assertIn(page, source)
        self.assertNotIn('"运行配置优化"', source)
        self.assertNotIn('"采购组合优化"', source)

    def test_collects_scoped_demand_and_pool_sharing(self):
        source = Path("app.py").read_text(encoding="utf-8")
        for label in ("GPU 型号", "地域", "不可共享", "团队内共享", "跨团队共享"):
            self.assertIn(label, source)

    def test_exposes_evidence_and_approval_state(self):
        source = Path("app.py").read_text(encoding="utf-8")
        for label in ("受影响资源", "观察期间", "待审批", "约束快照"):
            self.assertIn(label, source)


if __name__ == "__main__":
    unittest.main()
