import unittest

import pandas as pd

from src.workflow import ready_for_audit, ready_for_optimization


class WorkflowContractTest(unittest.TestCase):
    def test_requires_all_four_tables_and_no_mapping_errors(self):
        complete = {role: object() for role in ("inventory", "usage", "billing", "sla")}
        self.assertTrue(ready_for_audit(complete, {}))
        self.assertFalse(ready_for_audit({"inventory": object()}, {}))
        self.assertFalse(ready_for_audit(complete, {"billing": ["缺少净成本"]}))

    def test_optimization_requires_clean_audit_and_confirmed_constraints(self):
        self.assertFalse(ready_for_optimization(None, False))
        clean = pd.DataFrame([{"status": "通过", "severity": "阻断"}])
        blocked = pd.DataFrame([{"status": "异常", "severity": "阻断"}])
        self.assertTrue(ready_for_optimization(clean, True))
        self.assertFalse(ready_for_optimization(blocked, True))


if __name__ == "__main__":
    unittest.main()
