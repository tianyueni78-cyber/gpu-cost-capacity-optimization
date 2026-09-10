from io import BytesIO
import unittest

from src.action_io import read_actions_csv
from src.models import ActionStatus, ActionType


VALID_HEADER = (
    "action_id,action_type,resource_pool_id,owner,approved_at,"
    "planned_execution_at,estimated_savings_usd,implementation_cost_usd\n"
)


class ActionImportTest(unittest.TestCase):
    def test_imports_valid_action_with_approved_status(self):
        csv_file = BytesIO(
            (
                VALID_HEADER
                + "ACT-001,RIGHTSIZE,GPU-001,ops@example.com,2026-08-01,"
                "2026-08-10,1200,100\n"
            ).encode("utf-8")
        )

        result = read_actions_csv(csv_file)

        self.assertEqual(result.errors, ())
        self.assertEqual(len(result.records), 1)
        self.assertEqual(result.records[0].action_type, ActionType.RIGHTSIZE)
        self.assertEqual(result.records[0].status, ActionStatus.APPROVED)
        self.assertEqual(result.records[0].estimated_savings_usd, 1200.0)

    def test_rejects_action_without_resource_scope(self):
        csv_file = BytesIO(
            (
                VALID_HEADER
                + "ACT-002,RIGHTSIZE,,ops@example.com,2026-08-01,"
                "2026-08-10,1200,100\n"
            ).encode("utf-8")
        )

        result = read_actions_csv(csv_file)

        self.assertEqual(result.records, ())
        self.assertEqual(result.errors[0].row_number, 2)
        self.assertEqual(result.errors[0].field, "resource_pool_id")

    def test_reports_unknown_action_type_without_crashing(self):
        csv_file = BytesIO(
            (
                VALID_HEADER
                + "ACT-003,DELETE,GPU-003,ops@example.com,2026-08-01,"
                "2026-08-10,1200,100\n"
            ).encode("utf-8")
        )

        result = read_actions_csv(csv_file)

        self.assertEqual(result.records, ())
        self.assertEqual(result.errors[0].field, "action_type")
        self.assertIn("不支持", result.errors[0].message)


if __name__ == "__main__":
    unittest.main()
