import unittest
from pathlib import Path


class AppContractTest(unittest.TestCase):
    def test_app_exposes_exactly_four_forecast_pages(self):
        source = Path("app.py").read_text(encoding="utf-8")
        for page in ("数据与范围", "预测工作台", "容量情景", "计划与复盘"):
            self.assertIn(page, source)
        self.assertIn("本地演示模式", source)


if __name__ == "__main__":
    unittest.main()
