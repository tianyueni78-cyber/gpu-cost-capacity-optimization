from dataclasses import dataclass
from datetime import datetime

from .models import ActionStatus


ALLOWED_TRANSITIONS = {
    ActionStatus.PENDING_APPROVAL: {ActionStatus.APPROVED, ActionStatus.CANCELLED},
    ActionStatus.APPROVED: {ActionStatus.IN_PROGRESS, ActionStatus.CANCELLED},
    ActionStatus.IN_PROGRESS: {
        ActionStatus.EXECUTED,
        ActionStatus.CANCELLED,
        ActionStatus.ROLLED_BACK,
    },
    ActionStatus.EXECUTED: {
        ActionStatus.PENDING_VERIFICATION,
        ActionStatus.ROLLED_BACK,
    },
    ActionStatus.PENDING_VERIFICATION: {
        ActionStatus.VERIFIED,
        ActionStatus.PARTIALLY_REALIZED,
        ActionStatus.NOT_REALIZED,
        ActionStatus.NEGATIVE_IMPACT,
        ActionStatus.UNVERIFIABLE,
    },
}


@dataclass(frozen=True)
class ActionEvent:
    from_status: ActionStatus
    to_status: ActionStatus
    actor: str
    occurred_at: datetime
    note: str


def transition_action(
    current: ActionStatus,
    target: ActionStatus,
    actor: str,
    occurred_at: datetime,
    note: str,
) -> ActionEvent:
    if target not in ALLOWED_TRANSITIONS.get(current, set()):
        raise ValueError(f"不允许的状态转换：{current.value} → {target.value}")
    if not actor.strip():
        raise ValueError("操作者不能为空")
    if occurred_at.tzinfo is None:
        raise ValueError("发生时间必须包含时区")
    return ActionEvent(current, target, actor.strip(), occurred_at, note.strip())
