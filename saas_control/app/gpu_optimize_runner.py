"""Turn qualified GPU Data signals into conservative, auditable recommendations."""


RULES = {
    "high_cost_low_activity": (
        "审核停机窗口或调度释放",
        "活跃比例不高于 30% 的观测达到 75%，且相关成本占比达到 30%",
    ),
    "allocated_active_gap": (
        "核查分配与活跃差距，确认可缩减容量",
        "已分配 GPU 与活跃 GPU 的中位数差距达到 50%",
    ),
}


def build_recommendations(result: dict):
    if result.get("status") != "SUCCEEDED":
        return []
    coverage = result.get("summary", {}).get("gpu_telemetry_coverage_pct")
    recommendations = []
    for signal in result.get("signals", []):
        rule = RULES.get(signal.get("signal_type"))
        if not rule:
            continue
        action, threshold = rule
        recommendations.append({
            "recommendation_key": signal["signal_id"],
            "target": signal["scope"],
            "current_configuration": "保持现有配置，等待人工审核",
            "recommended_action": action,
            "trigger_metric": signal.get("evidence", ""),
            "observation_window": signal.get("period", ""),
            "rule_threshold": threshold,
            "evidence_coverage_pct": coverage,
            "related_cost_usd": float(signal.get("affected_cost_usd", 0)),
            "theoretical_savings_usd": 0.0,
            "evidence_level": "调查线索；需人工验证可回收性",
            "sla_risk": "未知：公开数据不含商业 SLA",
            "limitations": signal.get("limitation", "缺少可回收窗口和合同证据，不能计算节省。"),
            "manual_steps": "确认任务归属、峰值、队列、备用容量和回滚窗口后再批准。",
            "review_status": "待审核",
            "source_dataset_id": result.get("dataset_id"),
            "source_result_id": result.get("result_id"),
        })
    return recommendations
