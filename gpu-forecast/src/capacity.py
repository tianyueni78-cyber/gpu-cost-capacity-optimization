import math

import pandas as pd


SCOPE_COLUMNS = ["team_id", "workload_type", "gpu_model", "region"]
PERCENTILES = ("P50", "P90", "P99")


def build_capacity_scenarios(
    forecast,
    rules=None,
    inventory=None,
    *,
    productivity=None,
    sla_factor=1.0,
    uncertainty=1.0,
):
    """Convert demand forecasts into independently scoped GPU scenarios."""
    if not isinstance(forecast, pd.DataFrame):
        if productivity is None or productivity <= 0:
            raise ValueError("单位 GPU 有效产能必须大于零")
        planned = math.ceil(float(forecast) / productivity * sla_factor * uncertainty)
        return pd.DataFrame([{"forecast_value": forecast, "planned_gpu_count": planned}])

    if rules is None or rules.empty:
        raise ValueError("缺少容量规则")

    merged = forecast.merge(rules, on=SCOPE_COLUMNS, how="left", validate="many_to_one")
    if merged["productivity_per_gpu"].isna().any():
        raise ValueError("缺少容量规则")
    if (merged["productivity_per_gpu"] <= 0).any():
        raise ValueError("单位 GPU 有效产能必须大于零")

    inventory = inventory if inventory is not None else pd.DataFrame()
    available = _available_capacity(inventory)
    merged = merged.merge(available, on=["team_id", "gpu_model", "region"], how="left")
    merged["available_gpu_count"] = merged["available_gpu_count"].fillna(0)
    for optional in ("shared_gpu_count", "effective_incoming_gpu_count", "quota_gpu_count"):
        if optional not in merged:
            merged[optional] = 0
        merged[optional] = merged[optional].fillna(0)

    output = []
    for row in merged.to_dict("records"):
        for percentile in PERCENTILES:
            demand = float(row[percentile.lower()])
            base = math.ceil(demand / float(row["productivity_per_gpu"]))
            planned = math.ceil(
                demand
                / float(row["productivity_per_gpu"])
                * float(row.get("sla_safety_factor", 1.0))
                * float(row.get("uncertainty_factor", 1.0))
            )
            usable = row["available_gpu_count"] + row["shared_gpu_count"] + row["effective_incoming_gpu_count"]
            result = {key: row[key] for key in ["period", *SCOPE_COLUMNS]}
            result.update(
                percentile=percentile,
                forecast_value=demand,
                productivity_per_gpu=row["productivity_per_gpu"],
                base_gpu_count=base,
                planned_gpu_count=planned,
                available_gpu_count=int(row["available_gpu_count"]),
                shared_gpu_count=int(row["shared_gpu_count"]),
                effective_incoming_gpu_count=int(row["effective_incoming_gpu_count"]),
                quota_gpu_count=int(row["quota_gpu_count"]),
                shortfall_gpu_count=max(0, planned - int(usable)),
                rule_source=row.get("rule_source", "capacity_rules"),
            )
            output.append(result)
    return pd.DataFrame(output)


def _available_capacity(inventory):
    keys = ["team_id", "gpu_model", "region"]
    if inventory is None or inventory.empty:
        return pd.DataFrame(columns=[*keys, "available_gpu_count"])
    eligible = inventory.copy()
    if "procurement_model" in eligible:
        eligible = eligible[eligible["procurement_model"].str.casefold() != "spot"]
    return (
        eligible.groupby(keys, as_index=False)["gpu_count"]
        .sum()
        .rename(columns={"gpu_count": "available_gpu_count"})
    )
