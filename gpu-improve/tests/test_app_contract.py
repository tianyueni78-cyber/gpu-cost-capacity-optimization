from pathlib import Path
import unittest

from src.comparability import ComparabilityResult
from src.workflow import can_verify, persist_then_export


class AppContractTest(unittest.TestCase):
    def test_app_exposes_only_four_improve_pages(self):
        source = Path("app.py").read_text(encoding="utf-8")
        for page in ("行动导入", "执行台账", "收益验证", "收益复盘"):
            self.assertIn(page, source)
        self.assertNotIn("自动执行生产变更", source)

    def test_blocking_reason_prevents_verification(self):
        blocked = ComparabilityResult(False, ("币种不一致",), (), "UNVERIFIABLE")
        self.assertFalse(can_verify(blocked))

    def test_result_is_persisted_before_export(self):
        calls = []

        output = persist_then_export(
            {"action_id": "ACT-1"},
            save=lambda value: calls.append(("save", value)),
            export=lambda value: calls.append(("export", value)) or b"csv",
        )

        self.assertEqual([name for name, _ in calls], ["save", "export"])
        self.assertEqual(output, b"csv")


if __name__ == "__main__":
    unittest.main()
