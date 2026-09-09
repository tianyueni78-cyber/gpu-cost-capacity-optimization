"""把容量求解结果转换成可比较、不过度承诺的方案。"""

from src.capacity import CapacityInput, solve_capacity


def _row(
    scenario: str,
    allocated: int,
    reallocatable: int,
    affected_cost: float,
    shortfall: int = 0,
) -> dict:
    return {
        "scenario": scenario,
        "allocated_gpu_count": allocated,
        "reallocatable_gpu_count": reallocatable,
        "affected_cost_usd": affected_cost,
        "theoretical_savings_usd": 0.0,
        "sla_shortfall_gpu_count": shortfall,
        "assumption": "容量调整本身不等于账单节省；采购模块验证合同和费率后才能计算节省。",
    }


def build_capacity_scenarios(
    problem: CapacityInput, hourly_rate: float, hours: int
) -> list[dict]:
    current = sum(problem.current_allocations.values()) or problem.total_gpu_count
    rows = [_row("当前方案", current, 0, 0.0)]
    solution = solve_capacity(problem)
    if solution.status != "optimal":
        shortfall = max(
            0,
            sum(team.minimum_gpu_count for team in problem.teams)
            - problem.total_gpu_count,
        )
        rows.append(_row("无可行方案", current, 0, 0.0, shortfall))
        return rows

    reallocatable = solution.shared_gpu_count
    retained = sum(solution.team_allocations.values())
    affected_cost = round(reallocatable * float(hourly_rate) * int(hours), 2)
    rows.append(_row("安全释放", retained, reallocatable, affected_cost))

    low_change = reallocatable // 2
    rows.append(
        _row(
            "低变更",
            problem.total_gpu_count - low_change,
            low_change,
            round(low_change * float(hourly_rate) * int(hours), 2),
        )
    )
    return rows
