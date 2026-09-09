# Current State

## Current Goal

在四平台目录架构上继续产品开发：优先完成 GPU Improve，再完成 GPU Forecast；每个平台保持独立运行、独立测试和独立部署。

## Completed and Validated

- 仓库已重构为四个产品目录：`gpu-data/`、`gpu-optimize/`、`gpu-improve/`、`gpu-forecast/`。
- GPU Data 已迁入独立目录，包含入口、业务代码、测试、依赖、README 和试点文档；29 项测试、Python 编译和 Streamlit 健康检查通过。
- GPU Optimize 已迁入独立目录，包含入口、业务代码、测试、依赖、README 和试点文档；38 项测试、Python 编译和 Streamlit 健康检查通过。
- GPU Improve 与 GPU Forecast 已建立独立产品目录，README 明确标记为待开发，没有用空壳页面伪装成已完成功能。
- 根目录旧版 `app.py`、`src/`、`tests/`、统一 `requirements.txt` 已删除，其功能已由两个独立平台目录承接。
- 过程性 `docs/` 已从当前主线移除；永久文档整理为根目录 `产品设计.md` 和 `四平台正式规格.md`。
- 根 `README.md` 已更新为四平台导航、真实完成状态、运行方式和在线案例入口。
- `compact-context` skill 已安装到本机 Codex skills。

## Confirmed Decisions and Constraints

- 四个平台各自拥有运行所需代码，不依赖第五个共享代码目录。
- 允许复制少量稳定的数据接入和审计代码，以换取独立运行和部署；统一规格与平台测试负责防止口径漂移。
- GPU Data 负责可信数据、成本与资源基线和调查线索。
- GPU Optimize 负责约束下的配置方案；当前只完成容量优化阶段。
- GPU Improve 负责行动台账、前后对比和实际收益验证。
- GPU Forecast 负责时间回测、预测区间、容量情景和采购预算计划。
- 不把规划功能写成已上线；不自动修改生产资源；公开演示只使用合成数据。
- 理论节省、批准节省和实际收益必须分开。

## Relevant Files

- `README.md`：仓库总入口和四平台状态。
- `产品设计.md`：商业定位、边界和工作流。
- `四平台正式规格.md`：各平台输入、输出、规则和验收标准。
- `gpu-data/`：已完成的数据洞察平台。
- `gpu-optimize/`：已完成容量阶段的优化平台。
- `gpu-improve/README.md`：下一产品的边界。
- `gpu-forecast/README.md`：后续预测产品的边界。

## Unresolved

- GPU Improve 尚未设计和开发可运行应用。
- GPU Forecast 尚未设计和开发可运行应用。
- GPU Optimize 的采购组合与运行配置功能尚未完成。
- 功能分支和工作树暂时保留；主线稳定后再决定是否删除。

## Next Concrete Action

按 `四平台正式规格.md` 对 GPU Improve 做专业对标和独立设计，用户确认后采用测试优先实现“行动导入 → 执行台账 → 前后对比 → 收益复盘”。
