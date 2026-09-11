from dataclasses import dataclass
from enum import Enum


class Role(str, Enum):
    ORG_ADMIN = "ORG_ADMIN"
    ANALYST = "ANALYST"
    APPROVER = "APPROVER"
    VIEWER = "VIEWER"


class Product(str, Enum):
    DATA = "gpu-data"
    OPTIMIZE = "gpu-optimize"
    IMPROVE = "gpu-improve"
    FORECAST = "gpu-forecast"


class Permission(str, Enum):
    READ = "READ"
    EXPORT = "EXPORT"
    RUN_ANALYSIS = "RUN_ANALYSIS"
    APPROVE_ACTION = "APPROVE_ACTION"
    MANAGE_CONNECTORS = "MANAGE_CONNECTORS"
    MANAGE_MEMBERS = "MANAGE_MEMBERS"
    MANAGE_BILLING = "MANAGE_BILLING"


_ROLE_PERMISSIONS = {
    Role.ORG_ADMIN: set(Permission),
    Role.ANALYST: {Permission.READ, Permission.EXPORT, Permission.RUN_ANALYSIS},
    Role.APPROVER: {Permission.READ, Permission.EXPORT, Permission.APPROVE_ACTION},
    Role.VIEWER: {Permission.READ, Permission.EXPORT},
}
_READ_ONLY = {Permission.READ, Permission.EXPORT}


@dataclass(frozen=True)
class TenantContext:
    organization_id: str
    project_id: str
    user_id: str
    role: Role
    subscription_active: bool = True

    def __post_init__(self):
        if not self.organization_id or not self.project_id or not self.user_id:
            raise ValueError("组织、项目和用户不能为空")


def authorize(role: Role, permission: Permission, subscription_active: bool = True) -> None:
    if not subscription_active and permission not in _READ_ONLY:
        raise PermissionError("订阅已到期，当前为只读模式")
    if permission not in _ROLE_PERMISSIONS[role]:
        raise PermissionError("当前角色无权执行此操作")
