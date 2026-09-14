# Current State

## Current Goal

在现有统一网页中打通 GPU Data 真实闭环：样例/上传四表、持久化数据集、worker 调用既有审计与分析、保存并展示结果、下载报告。

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

以公开或脱敏真实数据验证 GPU Data 的字段映射和成本对账，再按同一最小闭环接入 GPU Optimize。
