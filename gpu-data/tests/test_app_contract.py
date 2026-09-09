import unittest

import pandas as pd

from src.workflow import ready_for_analysis, ready_for_audit


class WorkflowContractTest(unittest.TestCase):
    def test_requires_all_four_tables_and_no_mapping_errors(self):
        complete = {role: object() for role in ("inventory", "usage", "billing", "sla")}
        self.assertTrue(ready_for_audit(complete, {}))
        self.assertFalse(ready_for_audit({"inventory": object()}, {}))
        self.assertFalse(ready_for_audit(complete, {"billing": ["缺少净成本"]}))

    def test_analysis_requires_a_nonempty_audit_result(self):
        self.assertFalse(ready_for_analysis(pd.DataFrame()))

    def test_analysis_stops_on_abnormal_blocking_finding(self):
        audit_result = pd.DataFrame([
            {"severity": "阻断", "status": "异常"},
            {"severity": "警告", "status": "异常"},
        ])
        self.assertFalse(ready_for_analysis(audit_result))

    def test_analysis_allows_warnings_without_blocking_findings(self):
        audit_result = pd.DataFrame([
            {"severity": "阻断", "status": "通过"},
            {"severity": "警告", "status": "异常"},
        ])
        self.assertTrue(ready_for_analysis(audit_result))


if __name__ == "__main__":
    unittest.main()
