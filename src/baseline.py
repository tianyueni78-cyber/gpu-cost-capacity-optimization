"""GPU Data 的成本、容量与遥测现状指标。"""

import pandas as pd


def _numeric(frame: pd.DataFrame, field: str) -> pd.Series:
    return pd.to_numeric(frame[field], errors="coerce")


def _optional_quantile(frame: pd.DataFrame, field: str, quantile: float):
    if field not in frame:
        return pd.NA
    values = _numeric(frame, field).dropna()
    return float(values.quantile(quantile)) if not values.empty else pd.NA


def _coverage(frame: pd.DataFrame, field: str):
    if field not in frame:
        return pd.NA
    return float(frame[field].notna().mean() * 100)


def _attribute_billing(billing: pd.DataFrame, inventory: pd.DataFrame) -> pd.DataFrame:
    dimensions = inventory[["resource_pool_id", "team_id", "gpu_model", "region"]].copy()
    dimensions = dimensions.drop_duplicates("resource_pool_id").rename(columns={"team_id": "inventory_team_id"})
    attributed = billing.merge(dimensions, on="resource_pool_id", how="left", validate="many_to_one")

    if "team_id" in attributed:
        supplied_team = attributed["team_id"].astype("string").str.strip().replace("", pd.NA)
        attributed["team_id"] = supplied_team.fillna(attributed["inventory_team_id"])
    else:
        attributed["team_id"] = attributed["inventory_team_id"]
    return attributed.drop(columns="inventory_team_id")


def build_baseline(tables: dict[str, pd.DataFrame]) -> dict[str, pd.DataFrame]:
    inventory = tables["inventory"].copy()
    usage = tables["usage"].copy()
    billing = tables["billing"].copy()
    sla = tables["sla"].copy()

    for field in ("gross_cost_usd", "discount_usd", "net_cost_usd"):
        billing[field] = _numeric(billing, field)
    attributed = _attribute_billing(billing, inventory)

    cost_summary = pd.DataFrame([{
        "gross_cost_usd": float(billing["gross_cost_usd"].sum()),
        "discount_usd": float(billing["discount_usd"].sum()),
        "net_cost_usd": float(billing["net_cost_usd"].sum()),
    }])

    attributed["team_id"] = attributed["team_id"].fillna("未归属")
    breakdown_fields = ["invoice_month", "team_id", "gpu_model", "region", "procurement_model"]
    cost_breakdown = (
        attributed.groupby(breakdown_fields, dropna=False, as_index=False)[
            ["gross_cost_usd", "discount_usd", "net_cost_usd"]
        ].sum()
    )

    capacity_summary = pd.DataFrame([{
        "inventory_gpu_count": float(_numeric(inventory, "gpu_count").sum()),
        "median_allocated_gpu_count": _optional_quantile(usage, "allocated_gpu_count", 0.5),
        "median_active_gpu_count": _optional_quantile(usage, "active_gpu_count", 0.5),
        "p95_active_gpu_count": _optional_quantile(usage, "active_gpu_count", 0.95),
        "peak_active_gpu_count": float(_numeric(usage, "active_gpu_count").max()),
    }])

    usage_distribution = pd.DataFrame([{
        "median_gpu_utilization_pct": _optional_quantile(usage, "gpu_utilization_pct", 0.5),
        "p95_gpu_utilization_pct": _optional_quantile(usage, "gpu_utilization_pct", 0.95),
        "median_memory_utilization_pct": _optional_quantile(usage, "memory_utilization_pct", 0.5),
        "p95_memory_utilization_pct": _optional_quantile(usage, "memory_utilization_pct", 0.95),
    }])

    monitored_sla_fields = ("availability_pct", "p95_latency_ms", "queue_time_seconds")
    sla_summary = pd.DataFrame([{
        "sla_rule_count": len(sla),
        **{f"{field}_coverage_pct": _coverage(usage, field) for field in monitored_sla_fields},
    }])

    timestamps = pd.to_datetime(usage["timestamp_utc"], errors="coerce", utc=True)
    assigned_cost = attributed.loc[attributed["team_id"].ne("未归属"), "net_cost_usd"].sum()
    total_cost = attributed["net_cost_usd"].sum()
    cost_coverage = float(assigned_cost / total_cost * 100) if total_cost else pd.NA
    coverage = pd.DataFrame([{
        "usage_start_utc": timestamps.min(),
        "usage_end_utc": timestamps.max(),
        "usage_record_count": len(usage),
        "gpu_telemetry_coverage_pct": _coverage(usage, "gpu_utilization_pct"),
        "memory_telemetry_coverage_pct": _coverage(usage, "memory_utilization_pct"),
        "cost_attribution_coverage_pct": cost_coverage,
        "unassigned_net_cost_usd": float(total_cost - assigned_cost),
    }])

    return {
        "cost_summary": cost_summary,
        "cost_breakdown": cost_breakdown,
        "capacity_summary": capacity_summary,
        "usage_distribution": usage_distribution,
        "sla_summary": sla_summary,
        "coverage": coverage,
    }
