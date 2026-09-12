"""把三个 GPU 产品的现有导出组合成一次只读试点交付。"""

import json
import sys
from pathlib import Path

import pandas as pd


FILES = {
    "metrics": "metrics.csv",
    "signals": "signals.csv",
    "data_quality": "data_quality.csv",
    "recommendations": "recommendations.csv",
    "scenarios": "scenarios.csv",
    "approvals": "approvals.csv",
}


def load_pilot(input_dir: Path) -> dict:
    input_dir = Path(input_dir)
    required = ["project.json", *FILES.values()]
    missing = [name for name in required if not (input_dir / name).is_file()]
    if missing:
        raise ValueError(f"缺少试点文件：{', '.join(missing)}")

    data = {"project": json.loads((input_dir / "project.json").read_text(encoding="utf-8-sig"))}
    data.update({key: pd.read_csv(input_dir / name) for key, name in FILES.items()})
    benefits = input_dir / "benefits.csv"
    data["benefits"] = pd.read_csv(benefits) if benefits.is_file() else pd.DataFrame()
    return data


def build_actions(data: dict) -> pd.DataFrame:
    recommendations = data["recommendations"]
    approvals = data["approvals"]
    approved = recommendations.merge(approvals, on="recommendation_id", how="inner")
    rows = []
    for _, item in approved.iterrows():
        pools = [part.strip() for part in str(item["affected_resources"]).split(",") if part.strip()]
        cost_per_pool = float(item["implementation_cost_usd"]) / len(pools) if pools else 0
        for number, pool_id in enumerate(pools, start=1):
            rows.append({
                "action_id": f"{item['recommendation_id']}-{number}",
                "action_type": "RIGHTSIZE",
                "resource_pool_id": pool_id,
                "owner": item["owner"],
                "approved_at": item["approved_at"],
                "planned_execution_at": item["planned_execution_at"],
                "estimated_savings_usd": 0,
                "implementation_cost_usd": cost_per_pool,
            })
    return pd.DataFrame(rows, columns=[
        "action_id", "action_type", "resource_pool_id", "owner", "approved_at",
        "planned_execution_at", "estimated_savings_usd", "implementation_cost_usd",
    ])


def _sum(frame: pd.DataFrame, column: str) -> float:
    if frame.empty or column not in frame:
        return 0.0
    return float(pd.to_numeric(frame[column], errors="coerce").fillna(0).sum())


def _net_cost(metrics: pd.DataFrame) -> float:
    rows = metrics[(metrics["section"] == "cost_summary") & (metrics["metric"] == "net_cost_usd")]
    return _sum(rows, "value")


def _largest_scenario_cost(scenarios: pd.DataFrame) -> float:
    if scenarios.empty or "affected_cost_usd" not in scenarios:
        return 0.0
    return float(pd.to_numeric(scenarios["affected_cost_usd"], errors="coerce").fillna(0).max())


def build_executive_report(data: dict) -> str:
    project = data["project"]
    quality = data["data_quality"]
    abnormal = quality[quality["status"].eq("异常")] if "status" in quality else quality.iloc[0:0]
    issues = abnormal["message"].dropna().astype(str).tolist() if "message" in abnormal else []
    risks = data["recommendations"].get("sla_risk", pd.Series(dtype=str)).dropna().astype(str).tolist()
    benefits = data["benefits"]
    lines = [
        "# GPU 成本与利用率审计试点报告", "",
        f"- 客户：{project['customer']}",
        f"- 项目：{project['project_id']}",
        f"- 分析期间：{project['analysis_period']}", "",
        "## 管理层结论", "",
        f"- 已分析净成本：${_net_cost(data['metrics']):,.2f}",
        f"- 调查线索：{len(data['signals'])} 条",
        f"- 优化建议：{len(data['recommendations'])} 条",
        f"- 受影响成本：${_largest_scenario_cost(data['scenarios']):,.2f}",
        f"- 已验证收益：${_sum(benefits, '已验证收益（USD）'):,.2f}",
        f"- 成本规避：${_sum(benefits, '成本规避（USD）'):,.2f}", "",
        "受影响成本、已验证收益和成本规避使用不同口径，不合并为总节省。", "",
        "## 数据质量与风险", "",
    ]
    lines.extend(f"- {item}" for item in issues + risks)
    if not issues and not risks:
        lines.append("- 未发现已记录的异常或 SLA 风险。")
    lines.extend(["", "## 决策边界", "", "本报告为只读决策材料，不自动修改云资源、Kubernetes 或生产集群。"])
    return "\n".join(lines)


def run_pilot(input_dir: Path, output_dir: Path) -> None:
    data = load_pilot(input_dir)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    build_actions(data).to_csv(output_dir / "actions.csv", index=False, encoding="utf-8-sig")
    (output_dir / "executive-report.md").write_text(build_executive_report(data), encoding="utf-8")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        raise SystemExit("用法：python pilot.py <试点输入目录> <输出目录>")
    run_pilot(Path(sys.argv[1]), Path(sys.argv[2]))
