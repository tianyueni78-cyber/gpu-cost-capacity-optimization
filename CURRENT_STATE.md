# Current State

## Current Goal

用 Alibaba PAI 公开 GPU trace 与 Azure 官方零售价验证 GPU Data，并将通过质量门禁的分析结果接入 GPU Optimize，形成可审核、持久化的最小建议闭环。

## Completed and Validated

- 仓库已重构为四个产品目录：`gpu-data/`、`gpu-optimize/`、`gpu-improve/`、`gpu-forecast/`。
- GPU Data 已迁入独立目录，包含入口、业务代码、测试、依赖、README 和试点文档；29 项测试、Python 编译和 Streamlit 健康检查通过。
- GPU Optimize 已迁入独立目录，包含入口、业务代码、测试、依赖、README 和试点文档；38 项测试、Python 编译和 Streamlit 健康检查通过。
- GPU Improve 已实现行动导入、执行台账、收益验证和收益复盘四页流程，并具备 Supabase RLS 数据契约。
- GPU Forecast 已完成数据准备度、滚动回测、三类模型、版本化调整、容量情景、采购计划、四页 Streamlit 流程和安全存储契约。
- 根目录旧版 `app.py`、`src/`、`tests/`、统一 `requirements.txt` 已删除，其功能已由两个独立平台目录承接。
- 过程性 `docs/` 已从当前主线移除；永久文档整理为根目录 `产品设计.md` 和 `四平台正式规格.md`。
- 根 `README.md` 已更新为四平台导航、真实完成状态、运行方式和在线案例入口。
- `compact-context` skill 已安装到本机 Codex skills。
- GPU Improve 已完成专业对标和正式规格设计，覆盖行动台账、反事实基线、分类验证公式、证据等级、Supabase 数据模型和安全边界。
- 生产 SaaS 共享底座包含 RBAC/租户上下文、FastAPI 鉴权边界、PostgreSQL 多租户迁移、幂等任务、审计和 GPU Data 异步闭环；`saas_control/tests` 现有 36 项测试通过。
- 本地生产等价栈已实现：一条 PowerShell 命令启动 Next.js、FastAPI、PostgreSQL、Redis 和 worker；本地登录、组织/项目选择、四产品入口及任务状态可用。
- PostgreSQL 与 Redis 已通过显式 bind mount 固定到 `E:\DockerData\gpu-saas`；已实测容器重启后组织、项目和任务保留。
- 已实测服务健康、任务幂等与 worker 完成、PostgreSQL 跨租户 RLS 拒绝、Next.js 生产构建和四产品共 152 项回归测试。
- GPU Data 真实闭环已完成并实测：四表样例/上传、持久化数据集、异步真实分析、质量阻断、结果页和四类报告下载；样例得到 1100 USD、12 张 GPU、1 个闲置候选，坏数据被阻断且未发布正式成本。
- GPU Data 的幂等提交、四个下载文件、容器重启持久化、跨租户读写拒绝和 worker 依赖重启恢复均已实测。
- GPU Data 已使用 Alibaba PAI 2020 真实 T4 作业/传感器切片与 2026-09-14 查询的 Azure East US 官方公开零售价完成独立基准验证；20 张 GPU、2590.025833 GPU-hours、1362.353588 USD 对照成本、2.645860% 利用率中位数和 84.972965% P95 与产品结果一致。
- 公开数据转换保留来源、SHA-256、查询日期、字段证据和限制；团队、SLA、成本及活跃 GPU 等派生/合成字段没有写成源数据事实。
- normal、必需字段缺失和遥测缺失三个案例已通过真实 Docker API/worker 验证；两个异常案例均被质量门阻断，缺失利用率没有转成 0。
- 通过质量门的 GPU Data 信号可在统一网页进入 GPU Optimize；7 条建议已持久化，包含证据、观察窗口、阈值、覆盖率、相关成本、SLA 风险、限制、人工步骤、审核状态和来源 ID。公开证据不足时理论节省固定为 0。
- 公开闭环已实测重复生成幂等、报告下载、全栈重启后结果保留、另一租户读取为 0 和跨租户写入被 RLS 拒绝；PostgreSQL、Redis、API、worker、web 均健康。
- 完整回归共 194 项通过：SaaS 40、GPU Data 31、GPU Optimize 38、GPU Improve 45、GPU Forecast 40；Next.js 生产构建通过。

## Confirmed Decisions and Constraints

- 四个平台各自拥有运行所需代码，不依赖第五个共享代码目录。
- 允许复制少量稳定的数据接入和审计代码，以换取独立运行和部署；统一规格与平台测试负责防止口径漂移。
- GPU Data 负责可信数据、成本与资源基线和调查线索。
- GPU Optimize 负责约束下的配置方案；当前只完成容量优化阶段。
- GPU Improve 负责行动台账、前后对比和实际收益验证。
- GPU Forecast 负责时间回测、预测区间、容量情景和采购预算计划。
- 不把规划功能写成已上线；不自动修改生产资源；公开演示只使用合成数据。
- Docker 持久数据继续使用 E:\DockerData，不得迁移到 C 盘。
- 本阶段仅实现本地开发登录与受控产品入口；不实现正式连接器、支付、企业 SSO、备案或自动资源变更。
- 理论节省、批准节省和实际收益必须分开。
- 所有核心能力必须先对标 FinOps Foundation、FOCUS 或成熟专业平台，并记录采用、未采用部分及原因。
- GPU Improve 第一版采用 Streamlit + Supabase 免费数据库；邮箱登录、用户数据隔离，原始 CSV 不长期保存。

## Relevant Files

- `README.md`：仓库总入口和四平台状态。
- `产品设计.md`：商业定位、边界和工作流。
- `四平台正式规格.md`：各平台输入、输出、规则和验收标准。
- `gpu-data/`：已完成的数据洞察平台。
- `gpu-optimize/`：已完成容量阶段的优化平台。
- `gpu-improve/正式规格.md`：GPU Improve 的完整产品、数据、验证和安全规格。
- `gpu-improve/README.md`：GPU Improve 的状态和入口。
- `gpu-forecast/README.md`：后续预测产品的边界。
- `compose.yaml`、`.env.example`、`scripts/local-stack.ps1`：本地栈与单一启动入口。
- `saas_control/`：API、worker、多租户迁移、任务持久化和测试。
- `web/`：统一登录、租户选择、四产品入口、运行状态和任务页面。
- `docs/operations/local-stack.md`：普通 Windows 用户启动、停止和故障排查。

## Unresolved

- 统一 Next.js 当前提供受控产品页面和任务入口，尚未把四个 Streamlit 计算界面重写到统一前台。
- 尚未建立或配置对象存储、开发/预发布/生产环境；本阶段仅验证本地 PostgreSQL 与 Redis。
- AWS、Kubernetes/Prometheus 连接器尚未实施，四产品尚未接入持久化数据快照和异步任务。
- 支付宝、企业 SSO、订阅授权、人工开票流程、ICP/隐私协议/等保准备尚未实施。
- 监控告警、备份恢复、99.9% 可用性、RPO/RTO、负载与安全验收均未完成。
- GPU Optimize 的采购组合与运行配置能力仍未完成；任何产品都不自动修改客户生产资源。
- 功能分支和工作树暂时保留；主线稳定后再决定是否删除。

## Next Concrete Action

使用一份经脱敏的真实客户账单、集群遥测与 SLA 范围运行同一闭环，人工审核建议的可执行性，并把批准、执行和实际收益结果接入 GPU Improve；在此之前不宣称公开对照成本为客户成本，也不宣称节省金额。
