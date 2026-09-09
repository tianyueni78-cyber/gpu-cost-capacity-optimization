"""从资源池调整明细汇总容量方案与成本口径。"""

from src.capacity import CapacityInput, CapacitySolution


def build_capacity_scenarios(
    problem: CapacityInput,
    solution: CapacitySolution,
    period_hours: int,
) -> dict[str, list[dict]]:
    pools = {pool.resource_pool_id: pool for pool in problem.pools}
    details = []
    for adjustment in solution.adjustments:
        pool = pools[adjustment.resource_pool_id]
        affected_cost = round(
            adjustment.releasable_gpu_count
            * pool.hourly_rate_usd
            * int(period_hours),
            2,
        )
        details.append({
            "resource_pool_id": pool.resource_pool_id,
            "team_id": pool.team_id,
            "gpu_model": pool.gpu_model,
            "region": pool.region,
            "current_gpu_count": pool.gpu_count,
            "retained_gpu_count": adjustment.retained_gpu_count,
            "cross_team_shared_gpu_count": adjustment.cross_team_shared_gpu_count,
            "releasable_gpu_count": adjustment.releasable_gpu_count,
            "hourly_rate_usd": pool.hourly_rate_usd,
            "affected_cost_usd": affected_cost,
            "sharing_scope": pool.sharing_scope,
            "solver_status": solution.status,
        })

    current_count = sum(pool.gpu_count for pool in problem.pools)
    safe_releasable = sum(row["releasable_gpu_count"] for row in details)
    safe_cost = round(sum(row["affected_cost_usd"] for row in details), 2)
    shortfall = sum(
        int(part.split("缺少 ", 1)[1].split(" ", 1)[0])
        for part in solution.conflicts
        if "缺少 " in part
    )
    scenarios = [
        {
            "scenario": "当前方案",
            "allocated_gpu_count": current_count,
            "reallocatable_gpu_count": 0,
            "affected_cost_usd": 0.0,
            "theoretical_savings_usd": 0.0,
            "sla_shortfall_gpu_count": shortfall,
        }
    ]
    if details:
        scenarios.append({
            "scenario": "安全调整",
            "allocated_gpu_count": current_count - safe_releasable,
            "reallocatable_gpu_count": safe_releasable,
            "affected_cost_usd": safe_cost,
            "theoretical_savings_usd": 0.0,
            "sla_shortfall_gpu_count": shortfall,
        })
        low_change_count = safe_releasable // 2
        ratio = low_change_count / safe_releasable if safe_releasable else 0
        scenarios.append({
            "scenario": "低变更",
            "allocated_gpu_count": current_count - low_change_count,
            "reallocatable_gpu_count": low_change_count,
            "affected_cost_usd": round(safe_cost * ratio, 2),
            "theoretical_savings_usd": 0.0,
            "sla_shortfall_gpu_count": shortfall,
        })
    elif solution.status == "infeasible":
        scenarios.append({
            "scenario": "无可行方案",
            "allocated_gpu_count": current_count,
            "reallocatable_gpu_count": 0,
            "affected_cost_usd": 0.0,
            "theoretical_savings_usd": 0.0,
            "sla_shortfall_gpu_count": shortfall,
        })
    return {"scenarios": scenarios, "pool_adjustments": details}
