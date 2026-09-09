"""生成可追溯的容量建议与审批状态。"""

from copy import deepcopy

from src.capacity import CapacityInput, CapacitySolution


ALLOWED_STATUSES = {"待确认", "待审批", "推迟", "不适用"}


def build_recommendations(
    problem: CapacityInput,
    solution: CapacitySolution,
    scenario_result: dict,
    observation_period: str,
) -> list[dict]:
    scopes = sorted({pool.scope for pool in problem.pools})
    details = scenario_result.get("pool_adjustments", [])
    items = []
    for model, region in scopes:
        pools = [pool for pool in problem.pools if pool.scope == (model, region)]
        pool_ids = [pool.resource_pool_id for pool in pools]
        scope_details = [
            row for row in details
            if row.get("gpu_model") == model and row.get("region") == region
        ]
        affected_cost = round(sum(float(row.get("affected_cost_usd", 0)) for row in scope_details), 2)
        current_count = sum(pool.gpu_count for pool in pools)
        proposed_count = sum(int(row.get("retained_gpu_count", 0)) for row in scope_details) or current_count
        scope_conflicts = [item for item in solution.conflicts if f"{model} / {region}" in item]
        confirmed_requirements = {
            (item.team_id, item.gpu_model, item.region)
            for item in problem.requirements
        }
        confirmed = all(
            pool.sharing_confirmed
            and (pool.team_id, pool.gpu_model, pool.region) in confirmed_requirements
            for pool in pools
        )
        status = "待审批" if confirmed and not scope_conflicts else "待确认"
        items.append({
            "recommendation_id": f"{model}-{region}",
            "status": status,
            "observation": f"{model} / {region} 存在可评估的容量调整空间",
            "affected_resources": ", ".join(pool_ids),
            "period": observation_period,
            "current_configuration": f"当前 {current_count} 张 GPU",
            "proposed_configuration": f"建议保留 {proposed_count} 张 GPU",
            "constraints_met": "是" if not scope_conflicts else "否",
            "affected_cost_usd": affected_cost,
            "business_impact": "释放容量可用于同兼容范围内的其他需求或后续采购评估",
            "sla_risk": "低：硬约束已满足" if not scope_conflicts else "高：存在容量缺口",
            "limitation": "受影响成本不是已验证节省；不包含合同退出费用和采购折扣。",
            "owner_question": "是否确认共享边界并批准进入实施验证？",
        })
    return items


def set_recommendation_status(
    items: list[dict], recommendation_id: str, status: str
) -> list[dict]:
    if status not in ALLOWED_STATUSES:
        raise ValueError(f"不支持的建议状态：{status}")
    result = deepcopy(items)
    for item in result:
        if item["recommendation_id"] == recommendation_id:
            item["status"] = status
            return result
    raise ValueError(f"未找到建议：{recommendation_id}")
