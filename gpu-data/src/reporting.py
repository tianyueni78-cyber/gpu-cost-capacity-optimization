"""GPU Data 诊断报告和可复用 CSV 导出。"""

from datetime import datetime, timezone

import pandas as pd

from src.audit import AUDIT_COLUMNS
from src.signals import SIGNAL_COLUMNS


def _display(value) -> str:
    if pd.isna(value):
        return "数据不足"
    if isinstance(value, float):
        return f"{value:.2f}"
    return str(value)


def _metrics_frame(baseline: dict[str, pd.DataFrame]) -> pd.DataFrame:
    rows = []
    for section, frame in baseline.items():
        for row_number, (_, row) in enumerate(frame.iterrows(), start=1):
            for metric, value in row.items():
                name = metric if len(frame) == 1 else f"{row_number}.{metric}"
                rows.append({"section": section, "metric": name, "value": "" if pd.isna(value) else value})
    return pd.DataFrame(rows, columns=["section", "metric", "value"])


def _csv_bytes(frame: pd.DataFrame) -> bytes:
    return frame.to_csv(index=False).encode("utf-8-sig")


def build_csv_exports(baseline, signals, audit_result) -> dict[str, bytes]:
    return {
        "metrics.csv": _csv_bytes(_metrics_frame(baseline)),
        "signals.csv": _csv_bytes(signals.reindex(columns=SIGNAL_COLUMNS)),
        "data_quality.csv": _csv_bytes(audit_result.reindex(columns=AUDIT_COLUMNS)),
    }


def build_markdown_report(baseline, signals, audit_result, metadata=None) -> str:
    metadata = metadata or {}
    generated_at = metadata.get("generated_at") or datetime.now(timezone.utc).isoformat()
    period = metadata.get("analysis_period", "未指定")
    costs = baseline["cost_summary"].iloc[0]
    coverage = baseline["coverage"].iloc[0]
    attributed_total = pd.to_numeric(
        baseline["cost_breakdown"]["net_cost_usd"], errors="coerce"
    ).sum()
    reconciled = abs(float(costs["net_cost_usd"]) - float(attributed_total)) < 0.01

    lines = [
        "# GPU Data 诊断报告",
        "",
        f"- 分析期间：{period}",
        f"- 生成时间：{generated_at}",
        "",
        "## 成本概况",
        "",
        f"- 原始费用：${float(costs['gross_cost_usd']):.2f}",
        f"- 折扣：${float(costs['discount_usd']):.2f}",
        f"- 净成本：${float(costs['net_cost_usd']):.2f}",
        f"- 成本对账：{'通过' if reconciled else '未通过'}",
        "",
        "## 数据覆盖",
        "",
        f"- 使用记录：{_display(coverage['usage_record_count'])} 条",
        f"- GPU 遥测覆盖率：{_display(coverage['gpu_telemetry_coverage_pct'])}%",
        f"- 显存遥测覆盖率：{_display(coverage['memory_telemetry_coverage_pct'])}%",
        f"- 成本归属覆盖率：{_display(coverage['cost_attribution_coverage_pct'])}%",
        "",
        "## 数据质量警告",
        "",
    ]

    warnings = audit_result[
        audit_result["severity"].eq("警告") & audit_result["status"].eq("异常")
    ]
    if warnings.empty:
        lines.append("- 无异常警告。")
    else:
        for _, warning in warnings.iterrows():
            lines.append(f"- {warning['message']} 处理建议：{warning['action']}")

    lines.extend(["", "## 指标口径", ""])
    lines.extend([
        "- 净成本来自账单 `net_cost_usd`，归属前后必须对账。",
        "- GPU 核心利用率、显存利用率、已分配数量和活跃数量分别统计。",
        "- `数据不足` 表示对应遥测未提供，不代表数值为零。",
        "", "## 调查线索", "",
    ])

    if signals.empty:
        lines.append("未发现符合当前规则的调查线索。")
    else:
        for _, signal in signals.iterrows():
            lines.extend([
                f"### {signal['scope']}｜{signal['observation']}",
                "",
                f"- 证据：{signal['evidence']}",
                f"- 相关成本：${float(signal['affected_cost_usd']):.2f}",
                f"- 局限：{signal['limitation']}",
                f"- 核查问题：{signal['question']}",
                f"- 来源：{signal['source_tables']}；{signal['affected_rows']} 条记录",
                "",
            ])

    lines.extend([
        "## 使用边界", "",
        "本报告描述成本与资源观测事实及调查方向，不构成容量调整、采购或节省承诺。",
    ])
    return "\n".join(lines)
