# Current State

## Current Goal

完成 GPU Forecast 商业化正式规格评审，再制定测试优先实施计划；每个平台保持独立运行、独立测试和独立部署。

## Completed and Validated

- Data → Optimize → Improve 审计试点 CLI 已实现；它使用现有 CSV 导出生成 Improve 行动文件和管理层总报告，不引入共享运行服务。
- 合成试点数据覆盖人工批准、未批准建议、数据质量风险、已验证收益和成本规避。
- 真实客户试点包已建立，包含产品契约一致的空白 CSV、脱敏说明、30 分钟流程、审核清单和价格实验报价。
- 仓库已重构为四个产品目录：`gpu-data/`、`gpu-optimize/`、`gpu-improve/`、`gpu-forecast/`。
- GPU Data 已迁入独立目录，包含入口、业务代码、测试、依赖、README 和试点文档；29 项测试、Python 编译和 Streamlit 健康检查通过。
- GPU Optimize 已迁入独立目录，包含入口、业务代码、测试、依赖、README 和试点文档；38 项测试、Python 编译和 Streamlit 健康检查通过。
- GPU Improve 已实现行动导入、执行台账、收益验证和收益复盘四页流程，并具备 Supabase RLS 数据契约。
- GPU Forecast 已完成商业化定位、四页工作流、数据模型、预测与容量公式、安全边界及硬性验收规格。
- GPU Forecast 已建立独立产品目录，README 明确标记为待开发，没有用空壳页面伪装成已完成功能。
- 根目录旧版 `app.py`、`src/`、`tests/`、统一 `requirements.txt` 已删除，其功能已由两个独立平台目录承接。
- 过程性 `docs/` 已从当前主线移除；永久文档整理为根目录 `产品设计.md` 和 `四平台正式规格.md`。
- 根 `README.md` 已更新为四平台导航、真实完成状态、运行方式和在线案例入口。
- `compact-context` skill 已安装到本机 Codex skills。
- GPU Improve 已完成专业对标和正式规格设计，覆盖行动台账、反事实基线、分类验证公式、证据等级、Supabase 数据模型和安全边界。

## Confirmed Decisions and Constraints

- 四个平台各自拥有运行所需代码，不依赖第五个共享代码目录。
- 允许复制少量稳定的数据接入和审计代码，以换取独立运行和部署；统一规格与平台测试负责防止口径漂移。
- GPU Data 负责可信数据、成本与资源基线和调查线索。
- GPU Optimize 负责约束下的配置方案；当前只完成容量优化阶段。
- GPU Improve 负责行动台账、前后对比和实际收益验证。
- GPU Forecast 负责时间回测、预测区间、容量情景和采购预算计划。
- 不把规划功能写成已上线；不自动修改生产资源；公开演示只使用合成数据。
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
- `pilot.py`：三个已运行产品的文件交接和试点总报告入口。
- `examples/pilot/`：可直接运行的合成试点输入。
- `customer-pilot-pack/`：可直接发送给首批真实客户的试点准备与商业材料。

## Unresolved

- GPU Improve 的生产 Supabase 项目、正式部署和企业系统集成尚未实施。
- GPU Forecast 尚未开发可运行应用。
- GPU Optimize 的采购组合与运行配置功能尚未完成。
- 功能分支和工作树暂时保留；主线稳定后再决定是否删除。

## Next Concrete Action

用户审核 `gpu-forecast/正式规格.md`；确认后编写实施计划，不直接跳入开发。
