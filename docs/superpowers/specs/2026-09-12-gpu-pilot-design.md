# GPU 成本与利用率审计试点设计

## 目标

把 GPU Data、GPU Optimize 和 GPU Improve 的现有导出串成一次可交付试点。客户得到可信数据基线、待审批优化建议、行动交接和实际收益证据；GPU Forecast 暂不进入本轮。

## 市场切入口

首批客户是 GPU 月支出较高、没有专职 FinOps 团队、愿意提供脱敏 CSV，但暂时不愿授予生产权限的中小型 AI 公司。首次交付采用只读审计，不自动修改云资源。

## 最小架构

根目录增加一个标准库 CLI `pilot.py`。它读取一个试点目录中的 JSON 清单及三个产品已有的 CSV 导出，不导入三个产品内部代码，也不建立共享服务。输出包括：

1. `actions.csv`：把有独立人工批准记录的 Optimize 建议转换成 GPU Improve 已支持的行动格式；
2. `executive-report.md`：汇总成本、数据质量、调查线索、建议状态、受影响成本、已验证收益、成本规避和风险。

## 输入契约

必需文件：

- `project.json`：`project_id`、`customer`、`analysis_period`、`currency`；
- `metrics.csv`、`signals.csv`、`data_quality.csv`：GPU Data 现有导出；
- `recommendations.csv`、`scenarios.csv`：GPU Optimize 现有导出；
- `approvals.csv`：人工批准信息，包含建议编号、负责人、批准日期、计划执行日期和实施成本。

可选文件：

- `benefits.csv`：GPU Improve 收益台账；尚未执行行动时允许缺失。

## 关键规则

- 缺少必需文件或字段时停止，不生成看似完整的报告；
- 只有存在于 `approvals.csv` 的建议进入 `actions.csv`；
- `estimated_savings_usd` 固定为零，因为容量建议中的受影响成本不等于预计节省；
- 一条建议影响多个资源池时拆成多条行动；
- 已验证收益与成本规避分列，不能相加为“总节省”；
- 报告必须展示阻断项、SLA 风险和证据不足，不隐藏空值；
- 所有输出使用 UTF-8，CSV 带 BOM。

## 验收

- 合成数据能用一条命令生成两份输出；
- 生成的 `actions.csv` 能被 GPU Improve 的 `read_actions_csv` 无错误读取；
- 没有人工批准的建议不会生成行动；
- 报告中的成本、数量和收益可从输入 CSV 复算；
- 三个平台原有测试继续通过；
- 不新增第三方依赖。
