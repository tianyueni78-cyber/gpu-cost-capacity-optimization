"""把已审计数据转换为可追溯的调查线索，而不是优化建议。"""

import pandas as pd


SIGNAL_COLUMNS = [
    "signal_id", "signal_type", "priority", "scope", "period", "observation",
    "evidence", "affected_cost_usd", "limitation", "question", "source_tables",
    "affected_rows",
]

DEFAULT_SIGNAL_RULES = {
    "low_active_ratio_pct": 30.0,
    "sustained_low_observation_pct": 75.0,
    "high_cost_share_pct": 30.0,
    "allocation_gap_pct": 50.0,
    "committed_procurement_models": ("reserved", "savingsplan"),
}


def _period(frame: pd.DataFrame) -> str:
    timestamps = pd.to_datetime(frame["timestamp_utc"], errors="coerce", utc=True).dropna()
    if timestamps.empty:
        return "观测期间不可用"
    return f"{timestamps.min().date()} 至 {timestamps.max().date()}"


def _cost_by_pool(billing: pd.DataFrame) -> pd.Series:
    costs = billing.copy()
    costs["net_cost_usd"] = pd.to_numeric(costs["net_cost_usd"], errors="coerce")
    return costs.groupby("resource_pool_id", dropna=False)["net_cost_usd"].sum()


def _signal(signal_type, priority, scope, period, observation, evidence, affected_cost,
            limitation, question, source_tables, affected_rows):
    return {
        "signal_id": f"{scope}.{signal_type}",
        "signal_type": signal_type,
        "priority": priority,
        "scope": scope,
        "period": period,
        "observation": observation,
        "evidence": evidence,
        "affected_cost_usd": float(affected_cost),
        "limitation": limitation,
        "question": question,
        "source_tables": source_tables,
        "affected_rows": int(affected_rows),
    }


def build_investigation_signals(tables, baseline, rules=None) -> pd.DataFrame:
    active_rules = {**DEFAULT_SIGNAL_RULES, **(rules or {})}
    inventory = tables["inventory"].copy()
    usage = tables["usage"].copy()
    billing = tables["billing"].copy()
    sla = tables["sla"].copy()
    findings = []

    total_cost = float(baseline["cost_summary"].iloc[0]["net_cost_usd"])
    pool_costs = _cost_by_pool(billing)
    inventory_by_pool = inventory.drop_duplicates("resource_pool_id").set_index("resource_pool_id")

    usage["allocated_gpu_count"] = pd.to_numeric(usage["allocated_gpu_count"], errors="coerce")
    usage["active_gpu_count"] = pd.to_numeric(usage["active_gpu_count"], errors="coerce")
    usage["active_ratio_pct"] = usage["active_gpu_count"].div(
        usage["allocated_gpu_count"].where(usage["allocated_gpu_count"].gt(0))
    ) * 100

    for pool_id, pool_usage in usage.groupby("resource_pool_id", dropna=False):
        scope = str(pool_id)
        period = _period(pool_usage)
        affected_cost = float(pool_costs.get(pool_id, 0.0))
        cost_share = affected_cost / total_cost * 100 if total_cost else 0.0
        low_mask = pool_usage["active_ratio_pct"].le(active_rules["low_active_ratio_pct"])
        low_share = float(low_mask.mean() * 100)
        median_allocated = float(pool_usage["allocated_gpu_count"].median())
        median_active = float(pool_usage["active_gpu_count"].median())
        gap_pct = (median_allocated - median_active) / median_allocated * 100 if median_allocated else 0.0

        if low_share >= active_rules["sustained_low_observation_pct"] and cost_share >= active_rules["high_cost_share_pct"]:
            findings.append(_signal(
                "high_cost_low_activity", "高", scope, period,
                "该资源池同时具有较高成本占比和持续低活跃观测。",
                f"净成本 ${affected_cost:.2f}，占总净成本 {cost_share:.1f}%；{int(low_mask.sum())}/{len(pool_usage)} 条观测的活跃比例不高于 {active_rules['low_active_ratio_pct']:.0f}%。",
                affected_cost,
                "低活跃不等于浪费；采样间隔、峰值、备用容量和业务事件仍需核对。",
                "该期间是否存在未记录的峰值、待机要求或一次性业务事件？",
                "billing,usage", len(pool_usage),
            ))

        if gap_pct >= active_rules["allocation_gap_pct"]:
            findings.append(_signal(
                "allocated_active_gap", "中", scope, period,
                "已分配 GPU 数与活跃 GPU 数在多数观测中存在明显差距。",
                f"已分配数量中位数 {median_allocated:.1f}，活跃数量中位数 {median_active:.1f}，观测差距 {gap_pct:.1f}%。",
                affected_cost,
                "快照不能证明容量可被回收，且未反映任务排队、启动时间与冗余要求。",
                "分配但不活跃的容量分别由哪些任务、队列或保护策略占用？",
                "inventory,usage,billing", len(pool_usage),
            ))

        if pool_id in inventory_by_pool.index:
            procurement = str(inventory_by_pool.loc[pool_id].get("procurement_model", "")).lower()
            if procurement in active_rules["committed_procurement_models"] and low_share >= active_rules["sustained_low_observation_pct"]:
                findings.append(_signal(
                    "commitment_evidence", "中", scope, period,
                    "承诺采购资源在观测期间缺少充分的活跃使用证据。",
                    f"采购方式为 {procurement}；{int(low_mask.sum())}/{len(pool_usage)} 条观测处于低活跃范围；相关净成本 ${affected_cost:.2f}。",
                    affected_cost,
                    "当前数据不包含完整合同条款、取消限制和续约选择，相关成本不代表可立即减少的支出。",
                    "合同到期时间、承诺覆盖对象和续约责任人是否已经确认？",
                    "inventory,usage,billing", len(pool_usage),
                ))

    if "team_id" in billing:
        missing_owner = billing["team_id"].isna() | billing["team_id"].astype("string").str.strip().eq("")
        for pool_id, rows in billing.loc[missing_owner].groupby("resource_pool_id", dropna=False):
            affected_cost = float(pd.to_numeric(rows["net_cost_usd"], errors="coerce").sum())
            findings.append(_signal(
                "missing_attribution", "中", str(pool_id), str(rows["invoice_month"].min()),
                "账单记录缺少直接团队归属。",
                f"{len(rows)} 条账单记录缺少 team_id，相关净成本 ${affected_cost:.2f}。",
                affected_cost,
                "资源清单可能提供间接归属，但不能证明账单标签在整个期间持续正确。",
                "账单标签、资源池负责人和共享成本归属规则是否一致？",
                "billing,inventory", len(rows),
            ))

    if "availability_pct" in usage and "availability_target_pct" in sla:
        team_lookup = inventory_by_pool["team_id"]
        if "team_id" not in usage:
            usage["team_id"] = usage["resource_pool_id"].map(team_lookup)
        else:
            usage["team_id"] = usage["team_id"].fillna(usage["resource_pool_id"].map(team_lookup))
        targets = sla[["team_id", "availability_target_pct"]].dropna().drop_duplicates("team_id")
        checked = usage.merge(targets, on="team_id", how="inner", validate="many_to_one")
        checked["availability_pct"] = pd.to_numeric(checked["availability_pct"], errors="coerce")
        checked["availability_target_pct"] = pd.to_numeric(checked["availability_target_pct"], errors="coerce")
        misses = checked["availability_pct"].lt(checked["availability_target_pct"])
        for pool_id, rows in checked.loc[misses].groupby("resource_pool_id", dropna=False):
            affected_cost = float(pool_costs.get(pool_id, 0.0))
            findings.append(_signal(
                "sla_constraint", "高", str(pool_id), _period(rows),
                "观测可用性低于团队 SLA 目标。",
                f"{len(rows)} 条观测低于目标；最低可用性 {rows['availability_pct'].min():.2f}%，目标 {rows['availability_target_pct'].max():.2f}%。",
                affected_cost,
                "遥测异常不一定等于正式 SLA 违约，仍需核对计算窗口、排除期和事件记录。",
                "这些低于目标的观测是否对应已确认的服务事件？",
                "usage,sla,billing", len(rows),
            ))

    return pd.DataFrame(findings, columns=SIGNAL_COLUMNS)
