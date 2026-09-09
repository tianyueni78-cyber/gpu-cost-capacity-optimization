import unittest

from src.workflow import ready_for_audit


class WorkflowContractTest(unittest.TestCase):
    def test_requires_all_four_tables_and_no_mapping_errors(self):
        complete = {role: object() for role in ("inventory", "usage", "billing", "sla")}
        self.assertTrue(ready_for_audit(complete, {}))
        self.assertFalse(ready_for_audit({"inventory": object()}, {}))
        self.assertFalse(ready_for_audit(complete, {"billing": ["缺少净成本"]}))


if __name__ == "__main__":
    unittest.main()
