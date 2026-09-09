"""按 GPU 型号、地域和共享授权求解容量分配。"""

from dataclasses import dataclass
from math import ceil

import numpy as np
import pandas as pd
from scipy.optimize import Bounds, LinearConstraint, milp


SHARING_SCOPES = {"none", "team", "cross_team"}


@dataclass(frozen=True)
class ResourcePool:
    resource_pool_id: str
    team_id: str
    gpu_model: str
    region: str
    gpu_count: int
    hourly_rate_usd: float
    sharing_scope: str

    @property
    def scope(self) -> tuple[str, str]:
        return self.gpu_model, self.region


@dataclass(frozen=True)
class TeamRequirement:
    team_id: str
    gpu_model: str
    region: str
    confirmed_demand: int
    spare_capacity_pct: float
    minimum_gpu_count: int

    @property
    def scope(self) -> tuple[str, str]:
        return self.gpu_model, self.region


@dataclass(frozen=True)
class CapacityInput:
    pools: tuple[ResourcePool, ...]
    requirements: tuple[TeamRequirement, ...]


@dataclass(frozen=True)
class PoolAdjustment:
    resource_pool_id: str
    retained_gpu_count: int
    cross_team_shared_gpu_count: int
    releasable_gpu_count: int


@dataclass(frozen=True)
class CapacitySolution:
    status: str
    adjustments: tuple[PoolAdjustment, ...]
    shared_by_scope: dict[tuple[str, str], int]
    conflicts: tuple[str, ...]


def peak_demands(
    inventory: pd.DataFrame, usage: pd.DataFrame
) -> dict[tuple[str, str, str], int]:
    identity = inventory[["resource_pool_id", "team_id", "gpu_model", "region"]].drop_duplicates("resource_pool_id")
    observations = usage.drop(columns=["team_id", "gpu_model", "region"], errors="ignore").merge(
        identity, on="resource_pool_id", how="left"
    )
    active = pd.to_numeric(observations["active_gpu_count"], errors="coerce").fillna(0)
    grouped = active.groupby(
        [observations["team_id"], observations["gpu_model"], observations["region"]]
    ).max()
    return {tuple(key): int(value) for key, value in grouped.items()}


def build_capacity_input(
    tables: dict[str, pd.DataFrame],
    confirmed_demands: dict[tuple[str, str, str], int],
    sharing_scopes: dict[str, str],
) -> CapacityInput:
    inventory = tables.get("inventory", pd.DataFrame())
    sla = tables.get("sla", pd.DataFrame())
    pools = tuple(
        ResourcePool(
            str(row.resource_pool_id).strip(),
            str(row.team_id).strip(),
            str(row.gpu_model).strip(),
            str(row.region).strip(),
            int(row.gpu_count),
            float(row.effective_hourly_rate_usd),
            sharing_scopes.get(str(row.resource_pool_id).strip(), "none"),
        )
        for row in inventory.itertuples(index=False)
    )
    spare_by_team_region = (
        sla.groupby(["team_id", "region"])["min_spare_capacity_pct"].max().to_dict()
        if not sla.empty
        else {}
    )
    requirements = tuple(
        TeamRequirement(
            str(team).strip(),
            str(model).strip(),
            str(region).strip(),
            int(demand),
            float(spare_by_team_region.get((team, region), 0)),
            ceil(int(demand) * (1 + float(spare_by_team_region.get((team, region), 0)) / 100)),
        )
        for (team, model, region), demand in sorted(confirmed_demands.items())
    )
    return CapacityInput(pools, requirements)


def validate_capacity_input(problem: CapacityInput) -> list[str]:
    errors = []
    pool_ids = [pool.resource_pool_id for pool in problem.pools]
    if len(pool_ids) != len(set(pool_ids)):
        errors.append("资源池编号必须唯一")
    for pool in problem.pools:
        if pool.sharing_scope not in SHARING_SCOPES:
            errors.append(f"资源池 {pool.resource_pool_id} 的共享范围无效")
        if pool.gpu_count < 0 or pool.hourly_rate_usd < 0:
            errors.append(f"资源池 {pool.resource_pool_id} 的数量和费率不能为负")
    inventory_scopes = {pool.scope for pool in problem.pools}
    if not problem.requirements:
        errors.append("至少确认一个团队需求")
    for requirement in problem.requirements:
        if requirement.confirmed_demand < 0 or not 0 <= requirement.spare_capacity_pct <= 100:
            errors.append(f"需求 {requirement.team_id} / {requirement.gpu_model} / {requirement.region} 的数值无效")
        if requirement.scope not in inventory_scopes:
            errors.append(f"需求 {requirement.team_id} / {requirement.gpu_model} / {requirement.region} 没有匹配的库存")
    return errors


def _accessible_count(requirement: TeamRequirement, pools: list[ResourcePool]) -> int:
    return sum(
        pool.gpu_count
        for pool in pools
        if pool.team_id == requirement.team_id or pool.sharing_scope == "cross_team"
    )


def solve_capacity(problem: CapacityInput) -> CapacitySolution:
    conflicts = []
    adjustments = []
    shared_by_scope = {}
    scopes = sorted({pool.scope for pool in problem.pools} | {item.scope for item in problem.requirements})

    for scope in scopes:
        pools = [pool for pool in problem.pools if pool.scope == scope]
        requirements = [item for item in problem.requirements if item.scope == scope]
        scope_has_conflict = False
        for requirement in requirements:
            shortfall = requirement.minimum_gpu_count - _accessible_count(requirement, pools)
            if shortfall > 0:
                conflicts.append(
                    f"{requirement.team_id} / {scope[0]} / {scope[1]} 缺少 {shortfall} 张 GPU"
                )
                scope_has_conflict = True
        if scope_has_conflict:
            continue

        teams = [item.team_id for item in requirements]
        variables = [
            (pool, team)
            for pool in pools
            for team in teams
            if team == pool.team_id or pool.sharing_scope == "cross_team"
        ]
        if not variables:
            continue
        objective = np.array([pool.hourly_rate_usd + (0.0001 if team != pool.team_id else 0) for pool, team in variables])
        lower = np.zeros(len(variables))
        upper = np.array([pool.gpu_count for pool, _ in variables], dtype=float)
        constraints = []
        for pool in pools:
            row = np.array([1.0 if item_pool == pool else 0.0 for item_pool, _ in variables])
            if pool.sharing_scope == "none":
                constraints.append(LinearConstraint(row, pool.gpu_count, pool.gpu_count))
            else:
                constraints.append(LinearConstraint(row, 0, pool.gpu_count))
        for requirement in requirements:
            row = np.array([1.0 if team == requirement.team_id else 0.0 for _, team in variables])
            constraints.append(LinearConstraint(row, requirement.minimum_gpu_count, np.inf))
        result = milp(objective, integrality=np.ones(len(variables)), bounds=Bounds(lower, upper), constraints=constraints)
        if not result.success:
            total_required = sum(item.minimum_gpu_count for item in requirements)
            total_available = sum(pool.gpu_count for pool in pools)
            conflicts.append(f"{scope[0]} / {scope[1]} 缺少 {max(0, total_required - total_available)} 张 GPU")
            continue
        values = np.rint(result.x).astype(int)
        scope_shared = 0
        for pool in pools:
            retained = sum(int(values[index]) for index, (item_pool, _) in enumerate(variables) if item_pool == pool)
            cross_shared = sum(
                int(values[index])
                for index, (item_pool, team) in enumerate(variables)
                if item_pool == pool and team != pool.team_id
            )
            scope_shared += cross_shared
            adjustments.append(
                PoolAdjustment(pool.resource_pool_id, retained, cross_shared, pool.gpu_count - retained)
            )
        shared_by_scope[scope] = scope_shared

    return CapacitySolution(
        "infeasible" if conflicts else "optimal",
        tuple(adjustments),
        shared_by_scope,
        tuple(conflicts),
    )
