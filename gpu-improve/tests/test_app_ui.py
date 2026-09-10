from pathlib import Path
import unittest


class AppUiTest(unittest.TestCase):
    def test_local_demo_mode_and_security_boundary_are_visible(self):
        source = Path("app.py").read_text(encoding="utf-8")
        self.assertIn("本地演示模式", source)
        self.assertIn("原始账单和使用 CSV 不上传数据库", source)
        self.assertIn("SUPABASE_ANON_KEY", source)

    def test_ui_uses_domain_functions(self):
        source = Path("app.py").read_text(encoding="utf-8")
        self.assertIn("verify_benefit", source)
        self.assertIn("check_comparability", source)
        self.assertIn("build_ledger", source)


if __name__ == "__main__":
    unittest.main()
