from collections.abc import Mapping
from pathlib import Path

import pandas as pd

from .contracts import ForecastInputs, ForecastScope, ReadinessIssue, ReadinessResult


REQUIRED_COLUMNS = {
    "business_history": {
        "period", "team_id", "workload_type", "gpu_model", "region",
        "business_volume", "volume_unit", "event_flag",
    },
    "resource_inventory": {
        "resource_pool_id", "team_id", "gpu_model", "region", "gpu_count",
        "procurement_model", "start_date", "end_date",
    },
    "capacity_rules": {
        "team_id", "workload_type", "gpu_model", "region",
        "productivity_per_gpu", "sla_safety_factor", "min_spare_capacity_pct",
    },
}


def _read_csv(path: str | Path, table_name: str) -> pd.DataFrame:
    frame = pd.read_csv(path)
    missing = REQUIRED_COLUMNS[table_name] - set(frame.columns)
    if missing:
        raise ValueError(f"{table_name} 缺少字段: {', '.join(sorted(missing))}")
    return frame


def read_forecast_inputs(files: Mapping[str, str | Path]) -> ForecastInputs:
    history = _read_csv(files["business_history"], "business_history")
    inventory = _read_csv(files["resource_inventory"], "resource_inventory")
    rules = _read_csv(files["capacity_rules"], "capacity_rules")

    history["period"] = pd.to_datetime(history["period"], errors="raise")
    history["business_volume"] = pd.to_numeric(history["business_volume"], errors="raise")
    history["event_flag"] = history["event_flag"].astype(str).str.lower().map(
        {"true": True, "false": False, "1": True, "0": False}
    )
    if history["event_flag"].isna().any():
        raise ValueError("business_history.event_flag 包含无法解析的布尔值")
    for column in ("start_date", "end_date"):
        inventory[column] = pd.to_datetime(inventory[column], errors="coerce")
    inventory["gpu_count"] = pd.to_numeric(inventory["gpu_count"], errors="raise")
    for column in ("productivity_per_gpu", "sla_safety_factor", "min_spare_capacity_pct"):
        rules[column] = pd.to_numeric(rules[column], errors="raise")
    return ForecastInputs(history, inventory, rules)


def _scope_rows(frame: pd.DataFrame, scope: ForecastScope) -> pd.DataFrame:
    mask = (
        frame["team_id"].isin(scope.team_ids)
        & frame["gpu_model"].isin(scope.gpu_models)
        & frame["region"].isin(scope.regions)
    )
    return frame.loc[mask].copy()


def assess_readiness(inputs: ForecastInputs, scope: ForecastScope) -> ReadinessResult:
    history = _scope_rows(inputs.business_history, scope)
    start, end = pd.Timestamp(scope.period_start), pd.Timestamp(scope.period_end)
    history = history.loc[history["period"].between(start, end)].sort_values("period")
    inventory = _scope_rows(inputs.resource_inventory, scope)
    rules = _scope_rows(inputs.capacity_rules, scope)

    blockers: list[str] = []
    warnings: list[str] = []
    issues: list[ReadinessIssue] = []

    def block(reason: str, impact: str, recommendation: str) -> None:
        if reason not in blockers:
            blockers.append(reason)
            issues.append(ReadinessIssue(reason, "BLOCK", "当前预测范围", impact, recommendation))

    unique_periods = pd.DatetimeIndex(history["period"].dropna().unique()).sort_values()
    if len(unique_periods) < scope.min_history_periods:
        block("连续历史少于12个周期", "回测证据不足", "补齐至少12个连续周期")
    expected = pd.date_range(start, end, freq=scope.frequency)
    if not expected.isin(unique_periods).all():
        block("历史时间不连续", "趋势和季节性可能失真", "补齐缺失周期或确认缺口原因")
    if history["volume_unit"].dropna().nunique() > 1:
        block("业务量单位在范围内发生变化", "不同单位不可直接比较", "按口径变化分段或统一换算")
    if inventory.empty:
        block("预测范围无法关联资源清单", "无法确认现有容量", "补齐团队、型号和区域映射")
    if rules.empty:
        block("预测范围缺少容量换算规则", "业务量无法换算为GPU容量", "补齐单位产能和SLA系数")
    if not history.empty and history["event_flag"].fillna(False).any():
        warning = "历史包含已标记业务事件峰值，已保留"
        warnings.append(warning)
        issues.append(ReadinessIssue(warning, "WARN", "当前预测范围", "模型误差可能增大", "在计划层确认事件影响"))

    coverage = {
        "history_period_pct": round(100 * len(unique_periods.intersection(expected)) / len(expected), 2)
        if len(expected) else 0.0,
        "inventory_link_pct": 100.0 if not inventory.empty else 0.0,
        "capacity_rule_pct": 100.0 if not rules.empty else 0.0,
    }
    grade = "UNVERIFIABLE" if blockers else ("MEDIUM" if warnings else "HIGH")
    return ReadinessResult(not blockers, grade, tuple(blockers), tuple(warnings), coverage, tuple(issues))
