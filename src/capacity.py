"""GPU 容量约束与可解释的整数分配求解。"""

from dataclasses import dataclass
from math import ceil

import numpy as np
import pandas as pd
from scipy.optimize import Bounds, LinearConstraint, milp


@dataclass(frozen=True)
class TeamRequirement:
    team_id: str
    confirmed_demand: int
    spare_capacity_pct: float
    minimum_gpu_count: int


@dataclass(frozen=True)
class CapacityInput:
    total_gpu_count: int
    teams: tuple[TeamRequirement, ...]
    current_allocations: dict[str, int]


@dataclass(frozen=True)
class CapacitySolution:
    status: str
    team_allocations: dict[str, int]
    shared_gpu_count: int
    conflicts: tuple[str, ...]


def build_capacity_input(
    tables: dict[str, pd.DataFrame], confirmed_demands: dict[str, int]
) -> CapacityInput:
    inventory = tables.get("inventory", pd.DataFrame())
    sla = tables.get("sla", pd.DataFrame())
    spare_by_team = (
        sla.groupby("team_id")["min_spare_capacity_pct"].max().to_dict()
        if not sla.empty
        else {}
    )
    teams = tuple(
        TeamRequirement(
            team_id=team,
            confirmed_demand=int(demand),
            spare_capacity_pct=float(spare_by_team.get(team, 0)),
            minimum_gpu_count=ceil(
                int(demand) * (1 + float(spare_by_team.get(team, 0)) / 100)
            ),
        )
        for team, demand in sorted(confirmed_demands.items())
    )
    if inventory.empty:
        allocations = {}
        total = 0
    else:
        counts = pd.to_numeric(inventory["gpu_count"], errors="coerce").fillna(0)
        allocations = counts.groupby(inventory["team_id"]).sum().astype(int).to_dict()
        total = int(counts.sum())
    return CapacityInput(total, teams, allocations)


def validate_capacity_input(problem: CapacityInput) -> list[str]:
    errors = []
    if not problem.teams:
        errors.append("至少确认一个团队需求")
    if any(
        team.confirmed_demand < 0 or not 0 <= team.spare_capacity_pct <= 100
        for team in problem.teams
    ):
        errors.append("需求必须非负，备用容量必须在 0% 到 100% 之间")
    return errors


def solve_capacity(problem: CapacityInput) -> CapacitySolution:
    required = sum(team.minimum_gpu_count for team in problem.teams)
    if required > problem.total_gpu_count:
        shortfall = required - problem.total_gpu_count
        return CapacitySolution(
            "infeasible", {}, 0, (f"缺少 {shortfall} 张 GPU",)
        )

    lower = np.array(
        [team.minimum_gpu_count for team in problem.teams] + [0.0]
    )
    upper = np.full(len(lower), problem.total_gpu_count, dtype=float)
    objective = np.array([0.0] * len(problem.teams) + [-1.0])
    total = LinearConstraint(
        np.ones((1, len(lower))),
        problem.total_gpu_count,
        problem.total_gpu_count,
    )
    result = milp(
        objective,
        integrality=np.ones(len(lower)),
        bounds=Bounds(lower, upper),
        constraints=total,
    )
    if not result.success:
        return CapacitySolution("infeasible", {}, 0, (str(result.message),))

    values = np.rint(result.x).astype(int)
    allocations = {
        team.team_id: int(values[index])
        for index, team in enumerate(problem.teams)
    }
    return CapacitySolution("optimal", allocations, int(values[-1]), ())
