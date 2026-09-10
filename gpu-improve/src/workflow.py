from datetime import date
from io import BytesIO

import pandas as pd

from .comparability import ComparabilityResult
from .measurement import MetricSnapshot


def database_configured(secrets) -> bool:
    try:
        return bool(secrets.get("SUPABASE_URL") and secrets.get("SUPABASE_ANON_KEY"))
    except Exception:
        return False


def can_verify(comparability: ComparabilityResult) -> bool:
    return comparability.allowed and not comparability.blocking_reasons


def persist_then_export(result, save, export) -> bytes:
    save(result)
    return export(result)


def read_metric_snapshot(payload: bytes, expected_action_id: str) -> MetricSnapshot:
    frame = pd.read_csv(BytesIO(payload))
    if len(frame) != 1:
        raise ValueError("指标 CSV 必须且只能包含一行汇总数据")
    row = frame.iloc[0]
    if str(row["action_id"]) != expected_action_id:
        raise ValueError("指标 CSV 的行动编号与所选行动不一致")

    def optional_number(name):
        value = row.get(name)
        return None if pd.isna(value) else float(value)

    return MetricSnapshot(
        action_id=expected_action_id,
        resource_pool_ids=tuple(part.strip() for part in str(row["resource_pool_ids"]).split("|") if part.strip()),
        period_start=date.fromisoformat(str(row["period_start"])),
        period_end=date.fromisoformat(str(row["period_end"])),
        currency=str(row["currency"]),
        cost_basis=str(row["cost_basis"]),
        volume_unit=str(row["volume_unit"]),
        variable_cost_usd=float(row["variable_cost_usd"]),
        fixed_cost_usd=float(row["fixed_cost_usd"]),
        business_volume=float(row["business_volume"]),
        availability_pct=optional_number("availability_pct"),
        p95_latency_ms=optional_number("p95_latency_ms"),
        queue_time_seconds=optional_number("queue_time_seconds"),
        failure_rate_pct=optional_number("failure_rate_pct"),
        spare_capacity_pct=optional_number("spare_capacity_pct"),
        throughput_per_second=optional_number("throughput_per_second"),
        on_demand_equivalent_cost_usd=optional_number("on_demand_equivalent_cost_usd"),
        planned_purchase_cost_usd=optional_number("planned_purchase_cost_usd"),
    )
