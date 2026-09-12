import csv
import importlib.util
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def table_specs():
    spec = importlib.util.spec_from_file_location("gpu_data_schema", ROOT / "gpu-data/src/schema.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.TABLE_SPECS


class CustomerPilotPackTest(unittest.TestCase):
    def test_templates_match_product_contract_and_contain_no_rows(self):
        for role, definition in table_specs().items():
            path = ROOT / "customer-pilot-pack/templates" / f"{role}.csv"
            with path.open(encoding="utf-8-sig", newline="") as source:
                rows = list(csv.reader(source))
            self.assertEqual(rows, [list(definition.required_fields + definition.optional_fields)])


if __name__ == "__main__":
    unittest.main()
