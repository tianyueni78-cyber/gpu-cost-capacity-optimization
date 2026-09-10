from dataclasses import asdict

import pandas as pd

from .benefits import BenefitResult


COLUMNS = [
    "项目",
    "行动编号",
    "负责人",
    "状态",
    "预计收益（USD）",
    "实施成本（USD）",
    "已验证收益（USD）",
    "成本规避（USD）",
    "证据等级",
    "验证方法",
    "SLA结论",
    "原因",
]


def build_ledger(
    results: list[BenefitResult], action_details: dict[str, dict] | None = None
) -> pd.DataFrame:
    details = action_details or {}
    rows = []
    latest = {item.action_id: item for item in results}
    for item in latest.values():
        action = details.get(item.action_id, {})
        rows.append(
            {
                "项目": action.get("project", "本地演示"),
                "行动编号": item.action_id,
                "负责人": action.get("owner", "未指定"),
                "状态": action.get("status", item.outcome),
                "预计收益（USD）": action.get("estimated_savings_usd", 0),
                "实施成本（USD）": item.implementation_cost_usd,
                "已验证收益（USD）": item.realized_savings_usd,
                "成本规避（USD）": item.avoided_cost_usd,
                "证据等级": item.evidence_grade,
                "验证方法": item.method_id,
                "SLA结论": "负面影响" if item.outcome == "NEGATIVE_IMPACT" else (
                    "无法验证" if item.outcome == "UNVERIFIABLE" else "通过"
                ),
                "原因": "；".join(item.reasons),
            }
        )
    return pd.DataFrame(rows, columns=COLUMNS)


def export_csv_bytes(frame: pd.DataFrame) -> bytes:
    return frame.to_csv(index=False).encode("utf-8-sig")


def render_executive_report(frame: pd.DataFrame) -> str:
    realized = float(frame["已验证收益（USD）"].sum()) if not frame.empty else 0
    avoided = float(frame["成本规避（USD）"].sum()) if not frame.empty else 0
    risks = frame.loc[frame["SLA结论"] != "通过", "原因"].dropna().tolist()
    risk_text = "；".join(filter(None, risks)) or "未发现已记录的重大副作用"
    evidence = ", ".join(sorted(set(frame["证据等级"].astype(str)))) if not frame.empty else "无"
    methods = ", ".join(sorted(set(frame["验证方法"].astype(str)))) if not frame.empty else "无"
    return (
        "# 管理层收益复盘\n\n"
        "## 结论\n\n"
        f"已验证收益为 **${realized:,.2f}**；成本规避为 **${avoided:,.2f}**，二者未合并计算。\n\n"
        "## 证据与方法\n\n"
        f"- 证据等级：{evidence}\n"
        f"- 验证方法：{methods}\n\n"
        "## 风险与待决策事项\n\n"
        f"{risk_text}\n"
    )
