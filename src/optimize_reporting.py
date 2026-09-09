"""GPU Optimize 审批摘要与方案 CSV。"""

import pandas as pd


def build_approval_report(
    scope: dict, scenarios: list[dict], constraints: list[str]
) -> str:
    lines = [
        "# GPU Optimize 容量方案",
        "",
        "## 决策范围",
        "",
        f"- 分析期间：{scope.get('period', '未提供')}",
        "- 本报告只覆盖容量分配，不执行生产变更。",
        "",
        "## 已确认约束",
        "",
    ]
    lines.extend(f"- {constraint}" for constraint in constraints)
    lines.extend(["", "## 方案比较", ""])
    for row in scenarios:
        lines.extend([
            f"### {row['scenario']}",
            "",
            f"- 受影响成本：${float(row.get('affected_cost_usd', 0)):,.2f}",
            f"- 理论节省：${float(row.get('theoretical_savings_usd', 0)):,.2f}",
            "",
        ])
    lines.extend([
        "## 风险与假设",
        "",
        "受影响成本不是已验证节省。采购合同、退出费用和实际费率需由采购优化阶段复核。",
        "",
        "## 验证与回滚",
        "",
        "实施前应完成负载验证并记录原配置；出现容量或 SLA 异常时按客户流程回滚。",
        "",
        "## 审批",
        "",
        "最终是否实施由客户负责人审批。",
    ])
    return "\n".join(lines)


def scenarios_csv(scenarios: list[dict]) -> bytes:
    return pd.DataFrame(scenarios).to_csv(index=False).encode("utf-8-sig")
