from collections.abc import Callable

from fastapi import Header, HTTPException

from .domain import Role, TenantContext


def tenant_dependency(decode_token: Callable[[str], dict]):
    def current_tenant(authorization: str | None = Header(default=None)) -> TenantContext:
        if not authorization or not authorization.startswith("Bearer "):
            raise HTTPException(status_code=401, detail="需要有效登录")
        try:
            claims = decode_token(authorization.removeprefix("Bearer "))
            return TenantContext(
                organization_id=claims["organization_id"],
                project_id=claims["project_id"],
                user_id=claims["sub"],
                role=Role(claims["role"]),
                subscription_active=bool(claims.get("subscription_active", False)),
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise HTTPException(status_code=401, detail="需要有效登录") from exc

    return current_tenant
