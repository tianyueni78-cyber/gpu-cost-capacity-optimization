from dataclasses import dataclass
from datetime import datetime, timezone

from .domain import TenantContext


_SENSITIVE_MARKERS = ("token", "secret", "password", "credential", "key")


@dataclass(frozen=True)
class AuditEvent:
    organization_id: str
    project_id: str
    actor_user_id: str
    action: str
    resource_type: str
    resource_id: str
    metadata: dict
    created_at: datetime


def audit_event(context, action, resource_type, resource_id, metadata):
    safe = {
        key: value for key, value in metadata.items()
        if not any(marker in key.casefold() for marker in _SENSITIVE_MARKERS)
    }
    return AuditEvent(
        context.organization_id, context.project_id, context.user_id,
        action, resource_type, resource_id, safe, datetime.now(timezone.utc),
    )


def public_error(_error):
    return "INTERNAL_OPERATION_FAILED"
