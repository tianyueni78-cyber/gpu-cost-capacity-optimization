# SaaS Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 建立四产品可共同依赖的生产级多租户控制层、API 契约和本地可验证运行栈。

**Architecture:** 新建 `platform/`，FastAPI 仅承载身份、租户、授权、任务与产品调用编排；现有四产品 Python 模块保持独立。PostgreSQL RLS 是最终隔离边界，Redis/Celery 承载长任务，Next.js 在下一独立计划中消费稳定 API。

**Tech Stack:** Python 3.11、FastAPI、Pydantic v2、PostgreSQL/Supabase、Redis/Celery、pytest、Docker Compose。

**Spec:** `docs/superpowers/specs/2026-09-11-production-saas-design.md`

## Global Constraints

- 不重写或移动现有四产品领域算法。
- 身份只从验证后的 JWT 得出，客户端 owner 字段一律忽略。
- 所有租户表必须启用 RLS；跨租户访问返回 404，避免对象枚举。
- 不提交密钥，不记录令牌、原始账单或完整个人信息。
- 后台任务必须幂等；连接器只读；任何产品不得自动修改生产资源。

---

### Task 1: 共享领域契约与 RBAC

**Files:** Create `platform/app/domain.py`, `platform/tests/test_domain.py`, `platform/pyproject.toml`.

**Interfaces:** `Role`、`Product`、`Permission` 枚举；`authorize(role, permission) -> None`；`TenantContext` 禁止空组织、项目或用户。

- [ ] 写测试覆盖四级角色、过期订阅读取/写入边界和非法上下文。
- [ ] 运行 `python -m unittest platform.tests.test_domain -v`，确认模块缺失。
- [ ] 实现最小权限矩阵与冻结上下文。
- [ ] 运行测试和全量四产品回归。
- [ ] 提交 `feat: add shared SaaS authorization contracts`。

### Task 2: FastAPI 租户边界

**Files:** Create `platform/app/main.py`, `platform/app/security.py`, `platform/tests/test_api_security.py`.

**Interfaces:** `GET /healthz`；`GET /v1/context`；JWT 验证器输出 `TenantContext`；受保护路由不接受 owner_id。

- [ ] 先写无令牌、伪造 owner、跨项目和健康检查测试并确认失败。
- [ ] 实现 JWT claim 校验、统一 401/403/404 和 request-id。
- [ ] 运行 API 安全测试、OpenAPI 生成和全量回归。
- [ ] 提交 `feat: enforce tenant context at the API boundary`。

### Task 3: PostgreSQL 多租户迁移

**Files:** Create `platform/migrations/001_control_plane.sql`, `platform/tests/test_migrations.py`.

**Interfaces:** organizations、memberships、projects、product_entitlements、subscriptions、connectors、jobs、audit_events；所有外键包含 organization_id。

- [ ] 先写表、复合外键、RLS、不可变审计和权限函数契约测试。
- [ ] 实现可重复执行的前向迁移以及拒绝审计更新/删除的触发器。
- [ ] 使用真实 PostgreSQL 集成测试验证两个租户互不可见。
- [ ] 提交 `feat: add tenant-isolated control plane schema`。

### Task 4: 幂等任务与审计

**Files:** Create `platform/app/jobs.py`, `platform/app/audit.py`, `platform/tests/test_jobs.py`.

**Interfaces:** `submit_job(context, product, operation, idempotency_key)`；状态仅允许合法转换；公开错误不包含凭据。

- [ ] 先写重复提交、非法状态、租户冲突、失败清洗测试。
- [ ] 实现存储无关的任务服务和结构化审计事件。
- [ ] 运行测试并提交 `feat: add idempotent job and audit services`。

### Task 5: 本地生产等价栈与 CI

**Files:** Create `compose.yaml`, `platform/Dockerfile`, `.github/workflows/saas-ci.yml`, `docs/operations/local-stack.md`.

**Interfaces:** API、worker、PostgreSQL、Redis、Supabase 服务健康检查；环境变量由 `.env.example` 描述。

- [ ] 先写静态契约测试，要求非 root 容器、固定镜像版本、健康检查和无硬编码密钥。
- [ ] 实现容器与 CI，CI 运行平台测试、四产品测试、依赖扫描和迁移测试。
- [ ] 启动本地栈，验证 `/healthz`、worker、数据库和 Redis。
- [ ] 提交 `build: add production-equivalent SaaS stack`。

### Task 6: 后续独立计划入口

**Files:** Create `docs/roadmap/production-saas.md`; modify root `README.md`, `CURRENT_STATE.md`.

**Interfaces:** 固定后续顺序：Next.js 壳与统一登录 → AWS/Kubernetes 连接器 → GPU Data → Optimize → Improve → Forecast → 支付/SSO/合规/灾备。

- [ ] 写文档测试，禁止把外部账号尚未验收的事项标成完成。
- [ ] 记录每阶段输入、发布门槛和阻塞凭据。
- [ ] 运行全部测试、编译、迁移和 `git diff --check`。
- [ ] 提交 `docs: define production SaaS delivery gates`。
