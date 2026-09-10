from dataclasses import dataclass
from datetime import date
from enum import Enum


class ActionType(str, Enum):
    RIGHTSIZE = "RIGHTSIZE"
    RATE_COMMITMENT = "RATE_COMMITMENT"
    GPU_MIGRATION = "GPU_MIGRATION"
    SCHEDULING = "SCHEDULING"
    AVOIDED_PURCHASE = "AVOIDED_PURCHASE"


class ActionStatus(str, Enum):
    PENDING_APPROVAL = "PENDING_APPROVAL"
    APPROVED = "APPROVED"
    IN_PROGRESS = "IN_PROGRESS"
    EXECUTED = "EXECUTED"
    PENDING_VERIFICATION = "PENDING_VERIFICATION"
    CANCELLED = "CANCELLED"
    ROLLED_BACK = "ROLLED_BACK"
    VERIFIED = "VERIFIED"
    PARTIALLY_REALIZED = "PARTIALLY_REALIZED"
    NOT_REALIZED = "NOT_REALIZED"
    NEGATIVE_IMPACT = "NEGATIVE_IMPACT"
    UNVERIFIABLE = "UNVERIFIABLE"


@dataclass(frozen=True)
class ActionRecord:
    action_id: str
    action_type: ActionType
    resource_pool_id: str
    owner: str
    approved_at: date
    planned_execution_at: date
    estimated_savings_usd: float
    implementation_cost_usd: float
    status: ActionStatus = ActionStatus.APPROVED


@dataclass(frozen=True)
class ImportErrorDetail:
    row_number: int
    field: str
    message: str


@dataclass(frozen=True)
class ImportResult:
    records: tuple[ActionRecord, ...]
    errors: tuple[ImportErrorDetail, ...]
