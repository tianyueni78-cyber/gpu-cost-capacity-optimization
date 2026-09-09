import ast
import unittest
from pathlib import Path


APP_PATH = Path(__file__).resolve().parents[1] / "app.py"


class AppUiContractTest(unittest.TestCase):
    def test_exposes_four_gpu_data_pages(self):
        tree = ast.parse(APP_PATH.read_text(encoding="utf-8"))
        page_names = None
        for node in tree.body:
            if isinstance(node, ast.Assign) and any(
                isinstance(target, ast.Name) and target.id == "PAGE_NAMES"
                for target in node.targets
            ):
                page_names = ast.literal_eval(node.value)
                break

        self.assertEqual(("数据接入", "当前状况", "调查线索", "诊断报告"), page_names)


if __name__ == "__main__":
    unittest.main()
