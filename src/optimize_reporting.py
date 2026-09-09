"""GPU Optimize 审批报告与 Excel 兼容 CSV。"""

import pandas as pd


def build_approval_report(
    scope: dict,
    scenarios: list[dict],
    constraints: list[str],
    recommendations: list[dict] | None = None,
    pool_adjustments: list[dict] | None = None,
) -> str:
    recommendations = recommendations or []
    pool_adjustments = pool_adjustments or []
    lines = [
        "# GPU Optimize 容量方案",
        "",
        "## 决策范围",
        "",
        f"- 观察期间：{scope.get('period', '未提供')}",
        "- 本报告只覆盖容量分配，不执行生产变更。",
        "",
        "## 约束快照",
        "",
    ]
    lines.extend(f"- {item}" for item in constraints)
    lines.extend(["", "## 方案比较", ""])
    for row in scenarios:
        lines.extend([
            f"### {row['scenario']}",
            "",
            f"- 受影响成本：${float(row.get('affected_cost_usd', 0)):,.2f}",
            f"- 理论节省：${float(row.get('theoretical_savings_usd', 0)):,.2f}",
            "",
        ])
    lines.extend(["## 建议证据", ""])
    for item in recommendations:
        lines.extend([
            f"### {item['recommendation_id']}｜{item['status']}",
            "",
            f"- 受影响资源：{item['affected_resources']}",
            f"- SLA 风险：{item['sla_risk']}",
            f"- 负责人问题：{item['owner_question']}",
            "",
        ])
    lines.extend([
        "## 资源池调整明细",
        "",
        f"共 {len(pool_adjustments)} 条资源池调整记录，详见导出 CSV。",
        "",
        "## 风险与限制",
        "",
        "受影响成本不是已验证节省。采购合同、退出费用和实际折扣需由采购优化阶段复核。",
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


def rows_csv(rows: list[dict]) -> bytes:
    return pd.DataFrame(rows).to_csv(index=False).encode("utf-8-sig")


scenarios_csv = rows_csv
