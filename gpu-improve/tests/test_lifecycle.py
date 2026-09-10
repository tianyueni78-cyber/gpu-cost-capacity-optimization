from datetime import datetime, timezone
import unittest

from src.lifecycle import transition_action
from src.models import ActionStatus


NOW = datetime(2026, 8, 11, tzinfo=timezone.utc)


class ActionLifecycleTest(unittest.TestCase):
    def test_creates_append_only_event_for_legal_transition(self):
        event = transition_action(
            ActionStatus.APPROVED,
            ActionStatus.IN_PROGRESS,
            "owner@example.com",
            NOW,
            "开始执行",
        )

        self.assertEqual(event.from_status, ActionStatus.APPROVED)
        self.assertEqual(event.to_status, ActionStatus.IN_PROGRESS)
        self.assertEqual(event.actor, "owner@example.com")
        self.assertEqual(event.occurred_at, NOW)

    def test_execution_cannot_jump_directly_to_verified(self):
        with self.assertRaisesRegex(ValueError, "不允许的状态转换"):
            transition_action(
                ActionStatus.APPROVED,
                ActionStatus.VERIFIED,
                "owner@example.com",
                NOW,
                "",
            )

    def test_terminal_status_cannot_transition_again(self):
        with self.assertRaisesRegex(ValueError, "不允许的状态转换"):
            transition_action(
                ActionStatus.VERIFIED,
                ActionStatus.IN_PROGRESS,
                "owner@example.com",
                NOW,
                "重新打开",
            )


if __name__ == "__main__":
    unittest.main()
