from collections.abc import Callable
from typing import Any
from uuid import uuid4

from fastapi import Depends, FastAPI, Header, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from .domain import Permission, Product, TenantContext, authorize
from .security import tenant_dependency


class LoginRequest(BaseModel):
    email: str
    password: str


class SelectRequest(BaseModel):
    organization_id: str
    project_id: str


class JobRequest(BaseModel):
    product: Product
    operation: str
    idempotency_key: str


def create_app(
    decode_token: Callable[[str], dict],
    *,
    store: Any | None = None,
    issue_token: Callable[[str, str | None, str | None], str] | None = None,
    dev_credentials: tuple[str, str, str] | None = None,
) -> FastAPI:
    app = FastAPI(title="GPU SaaS Control API", version="0.2.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:3000"],
        allow_methods=["*"],
        allow_headers=["*"],
    )
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

    if store is None:
        return app

    @app.post("/v1/dev/login")
    def dev_login(payload: LoginRequest):
        if dev_credentials is None or issue_token is None:
            raise HTTPException(status_code=404, detail="本地登录未启用")
        email, password, user_id = dev_credentials
        if (payload.email, payload.password) != (email, password):
            raise HTTPException(status_code=401, detail="邮箱或密码错误")
        tenants = store.authenticate(payload.email, payload.password)
        if not tenants:
            raise HTTPException(status_code=401, detail="邮箱或密码错误")
        return {"selection_token": issue_token(user_id, None, None), "tenants": tenants}

    @app.post("/v1/dev/select")
    def select_tenant(payload: SelectRequest, authorization: str | None = Header(default=None)):
        if issue_token is None or not authorization or not authorization.startswith("Bearer "):
            raise HTTPException(status_code=401, detail="需要有效登录")
        try:
            claims = decode_token(authorization.removeprefix("Bearer "))
            user_id = claims["sub"]
        except (KeyError, TypeError, ValueError) as exc:
            raise HTTPException(status_code=401, detail="需要有效登录") from exc
        if not store.has_access(user_id, payload.organization_id, payload.project_id):
            raise HTTPException(status_code=404, detail="项目不存在")
        return {"access_token": issue_token(user_id, payload.organization_id, payload.project_id)}

    @app.get("/v1/products")
    def products(tenant: TenantContext = Depends(current_tenant)):
        return {"products": store.products(tenant.organization_id)}

    @app.post("/v1/jobs", status_code=202)
    def submit_job(payload: JobRequest, tenant: TenantContext = Depends(current_tenant)):
        try:
            authorize(tenant.role, Permission.RUN_ANALYSIS, tenant.subscription_active)
        except PermissionError as exc:
            raise HTTPException(status_code=403, detail=str(exc)) from exc
        return store.submit_job(tenant, payload.product, payload.operation, payload.idempotency_key)

    @app.get("/v1/jobs")
    def jobs(tenant: TenantContext = Depends(current_tenant)):
        return {"jobs": store.list_jobs(tenant)}

    @app.get("/v1/system/status")
    def system_status(tenant: TenantContext = Depends(current_tenant)):
        return store.status()

    return app
