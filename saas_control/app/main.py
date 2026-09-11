from collections.abc import Callable
from uuid import uuid4

from fastapi import Depends, FastAPI, HTTPException, Request

from .domain import TenantContext
from .security import tenant_dependency


def create_app(decode_token: Callable[[str], dict]) -> FastAPI:
    app = FastAPI(title="GPU SaaS Control API", version="0.1.0")
    current_tenant = tenant_dependency(decode_token)

    @app.middleware("http")
    async def request_id(request: Request, call_next):
        response = await call_next(request)
        response.headers["x-request-id"] = request.headers.get("x-request-id") or str(uuid4())
        return response

    @app.get("/healthz")
    def health():
        return {"status": "ok"}

    @app.get("/v1/context")
    def context(tenant: TenantContext = Depends(current_tenant)):
        return {
            "organization_id": tenant.organization_id,
            "project_id": tenant.project_id,
            "user_id": tenant.user_id,
            "role": tenant.role,
            "subscription_active": tenant.subscription_active,
        }

    @app.get("/v1/projects/{project_id}")
    def project(project_id: str, tenant: TenantContext = Depends(current_tenant)):
        if project_id != tenant.project_id:
            raise HTTPException(status_code=404, detail="项目不存在")
        return {"project_id": project_id}

    return app
