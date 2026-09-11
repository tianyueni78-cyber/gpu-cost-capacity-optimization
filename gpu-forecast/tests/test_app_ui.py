import unittest
from pathlib import Path


class AppUiTest(unittest.TestCase):
    def test_streamlit_app_starts(self):
        try:
            from streamlit.testing.v1 import AppTest
        except ImportError:
            self.skipTest("Streamlit 未安装")
        app = AppTest.from_file(str(Path(__file__).parents[1] / "app.py")).run(timeout=10)
        self.assertEqual(app.exception, [])


if __name__ == "__main__":
    unittest.main()
