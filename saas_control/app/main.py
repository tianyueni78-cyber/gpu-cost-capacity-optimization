from collections.abc import Callable
import base64
import binascii
from pathlib import Path
from typing import Any
from uuid import uuid4

from fastapi import Depends, FastAPI, Header, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, Response
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


class DatasetFile(BaseModel):
    file_name: str
    content_base64: str


class DatasetUpload(BaseModel):
    files: dict[str, DatasetFile]


class AnalysisRequest(BaseModel):
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
        tenants = store.authenticate(user_id, payload.password)
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

    @app.post("/v1/gpu-data/datasets/sample", status_code=201)
    def sample_dataset(tenant: TenantContext = Depends(current_tenant)):
        try:
            authorize(tenant.role, Permission.RUN_ANALYSIS, tenant.subscription_active)
        except PermissionError as exc:
            raise HTTPException(status_code=403, detail=str(exc)) from exc
        return store.create_sample_dataset(tenant, Path(__file__).parents[2] / "gpu-data" / "sample_data")

    @app.post("/v1/gpu-data/datasets/public-case", status_code=201)
    def public_dataset(tenant: TenantContext = Depends(current_tenant)):
        try:
            authorize(tenant.role, Permission.RUN_ANALYSIS, tenant.subscription_active)
        except PermissionError as exc:
            raise HTTPException(status_code=403, detail=str(exc)) from exc
        source = Path(__file__).parents[2] / "gpu-data" / "validation" / "alibaba_t4" / "source"
        return store.create_public_dataset(tenant, source)

    @app.post("/v1/gpu-data/datasets", status_code=201)
    def upload_dataset(payload: DatasetUpload, tenant: TenantContext = Depends(current_tenant)):
        try:
            authorize(tenant.role, Permission.RUN_ANALYSIS, tenant.subscription_active)
        except PermissionError as exc:
            raise HTTPException(status_code=403, detail=str(exc)) from exc
        required = {"inventory", "usage", "billing", "sla"}
        if set(payload.files) != required:
            raise HTTPException(status_code=422, detail="必须同时提供 inventory、usage、billing 和 sla 四个 CSV")
        decoded = {}
        for role, item in payload.files.items():
            if not item.file_name.lower().endswith(".csv"):
                raise HTTPException(status_code=422, detail=f"{role} 只接受 CSV 文件")
            try:
                content = base64.b64decode(item.content_base64, validate=True)
            except (ValueError, binascii.Error) as exc:
                raise HTTPException(status_code=422, detail=f"{role} 文件内容无效") from exc
            if not content or len(content) > 10 * 1024 * 1024:
                raise HTTPException(status_code=422, detail=f"{role} 文件必须在 1 字节到 10 MB 之间")
            decoded[role] = (Path(item.file_name).name, content)
        try:
            return store.create_dataset(tenant, decoded, "UPLOAD")
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

    @app.get("/v1/gpu-data/datasets/{dataset_id}")
    def dataset(dataset_id: str, tenant: TenantContext = Depends(current_tenant)):
        item = store.get_dataset(tenant, dataset_id)
        if not item:
            raise HTTPException(status_code=404, detail="数据集不存在")
        return item

    @app.post("/v1/gpu-data/datasets/{dataset_id}/analyze", status_code=202)
    def analyze_dataset(dataset_id: str, payload: AnalysisRequest, tenant: TenantContext = Depends(current_tenant)):
        try:
            authorize(tenant.role, Permission.RUN_ANALYSIS, tenant.subscription_active)
        except PermissionError as exc:
            raise HTTPException(status_code=403, detail=str(exc)) from exc
        job = store.submit_gpu_data_analysis(tenant, dataset_id, payload.idempotency_key)
        if not job:
            raise HTTPException(status_code=404, detail="数据集不存在")
        return job

    @app.get("/v1/gpu-data/datasets/{dataset_id}/result")
    def analysis_result(dataset_id: str, tenant: TenantContext = Depends(current_tenant)):
        result = store.get_analysis(tenant, dataset_id)
        if not result:
            raise HTTPException(status_code=404, detail="分析结果尚未生成")
        return result

    @app.get("/v1/gpu-data/artifacts/{artifact_id}")
    def artifact(artifact_id: str, tenant: TenantContext = Depends(current_tenant)):
        item = store.get_artifact(tenant, artifact_id)
        if not item:
            raise HTTPException(status_code=404, detail="报告不存在")
        return FileResponse(item["storage_path"], filename=item["file_name"], media_type=item["mime_type"])

    @app.post("/v1/gpu-optimize/datasets/{dataset_id}/recommendations", status_code=201)
    def create_recommendations(dataset_id: str, tenant: TenantContext = Depends(current_tenant)):
        try:
            authorize(tenant.role, Permission.RUN_ANALYSIS, tenant.subscription_active)
            items = store.create_recommendations(tenant, dataset_id)
        except PermissionError as exc:
            raise HTTPException(status_code=403, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        if items is None:
            raise HTTPException(status_code=404, detail="尚无可用的 GPU Data 分析结果")
        return {"dataset_id": dataset_id, "recommendations": items}

    @app.get("/v1/gpu-optimize/datasets/{dataset_id}/recommendations")
    def recommendations(dataset_id: str, tenant: TenantContext = Depends(current_tenant)):
        return {"dataset_id": dataset_id, "recommendations": store.get_recommendations(tenant, dataset_id)}

    @app.get("/v1/gpu-optimize/datasets/{dataset_id}/report")
    def recommendation_report(dataset_id: str, tenant: TenantContext = Depends(current_tenant)):
        items = store.get_recommendations(tenant, dataset_id)
        lines = ["# GPU Optimize 建议报告", "", f"数据集：{dataset_id}", ""]
        for item in items:
            lines.extend([
                f"## {item['target']}｜{item['review_status']}",
                f"- 建议：{item['recommended_action']}",
                f"- 证据：{item['trigger_metric']}",
                f"- 观察窗口：{item['observation_window']}",
                f"- 规则阈值：{item['rule_threshold']}",
                f"- 证据覆盖率：{item['evidence_coverage_pct']}%",
                f"- 相关成本：${item['related_cost_usd']:.2f}",
                f"- 理论节省：${item['theoretical_savings_usd']:.2f}",
                f"- 证据等级：{item['evidence_level']}",
                f"- SLA 风险：{item['sla_risk']}",
                f"- 限制：{item['limitations']}",
                f"- 人工步骤：{item['manual_steps']}",
                f"- 来源结果：{item['source_result_id']}", "",
            ])
        return Response(
            "\n".join(lines), media_type="text/markdown; charset=utf-8",
            headers={"Content-Disposition": 'attachment; filename="gpu-optimize-report.md"'},
        )

    return app
