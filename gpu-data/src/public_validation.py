"""Convert a small, provenance-preserving public trace slice into GPU Data CSVs."""

import json
from pathlib import Path

import pandas as pd


BASE_TIME = pd.Timestamp("2020-07-01T00:00:00Z")


def _write(frame: pd.DataFrame, path: Path):
    frame.to_csv(path, index=False, encoding="utf-8-sig")


def _normal_tables(source: Path):
    jobs = pd.read_csv(source / "pai_job_table.csv")
    tasks = pd.read_csv(source / "pai_task_table.csv")
    sensors = pd.read_csv(source / "pai_sensor_table.csv")
    price = json.loads((source / "azure_retail_price.json").read_text(encoding="utf-8-sig"))

    tasks["gpu_count"] = (
        pd.to_numeric(tasks["inst_num"], errors="coerce")
        * pd.to_numeric(tasks["plan_gpu"], errors="coerce") / 100
    )
    task_summary = tasks.groupby("job_name", as_index=False).agg(
        gpu_count=("gpu_count", "sum"),
        gpu_model=("gpu_type", "first"),
        task_start=("start_time", "min"),
    )
    sensor_summary = sensors.groupby("job_name", as_index=False).agg(
        gpu_utilization_pct=("gpu_wrk_util", "mean"),
        observed_memory_gb=("avg_gpu_wrk_mem", "mean"),
    )
    rows = jobs.merge(task_summary, on="job_name", validate="one_to_one").merge(
        sensor_summary, on="job_name", how="left", validate="one_to_one"
    )
    rows["duration_seconds"] = rows["end_time"] - rows["start_time"]
    rows["billed_gpu_hours"] = rows["gpu_count"] * rows["duration_seconds"] / 3600
    rows["team_id"] = "derived-user-" + rows["user"].astype(str)
    rows["timestamp_utc"] = BASE_TIME + pd.to_timedelta(rows["end_time"], unit="s")
    rows["resource_pool_id"] = "pai-job-" + rows["job_name"].astype(str)
    rate = float(price["retailPrice"])

    inventory = rows[["resource_pool_id", "team_id", "gpu_model", "gpu_count"]].copy()
    inventory["region"] = "azure-eastus-comparator"
    inventory["procurement_model"] = "ondemand"
    inventory["effective_hourly_rate_usd"] = rate
    inventory["workload_type"] = "training-derived"

    usage = rows[["timestamp_utc", "resource_pool_id", "team_id", "gpu_count", "gpu_utilization_pct"]].copy()
    usage.insert(0, "usage_record_id", [f"pai-usage-{i:03d}" for i in range(len(usage))])
    usage["allocated_gpu_count"] = usage.pop("gpu_count")
    usage["active_gpu_count"] = usage["allocated_gpu_count"] * usage["gpu_utilization_pct"] / 100
    usage["memory_utilization_pct"] = pd.NA
    usage["queue_time_seconds"] = (rows["task_start"] - rows["start_time"]).clip(lower=0)
    usage["telemetry_status"] = usage["gpu_utilization_pct"].notna().map({True: "observed", False: "missing"})
    usage["timestamp_utc"] = usage["timestamp_utc"].map(lambda value: value.isoformat())

    billing = rows[["resource_pool_id", "team_id", "billed_gpu_hours"]].copy()
    billing.insert(0, "billing_line_id", [f"pai-bill-{i:03d}" for i in range(len(billing))])
    billing["invoice_month"] = "2020-07"
    billing["charge_type"] = "usage"
    billing["procurement_model"] = "ondemand"
    billing["unit_rate_usd"] = rate
    billing["gross_cost_usd"] = billing["billed_gpu_hours"] * rate
    billing["discount_usd"] = 0.0
    billing["net_cost_usd"] = billing["gross_cost_usd"]
    billing["currency"] = price["currencyCode"]

    teams = sorted(rows["team_id"].unique())
    sla = pd.DataFrame({
        "sla_id": [f"synthetic-sla-{i:03d}" for i in range(len(teams))],
        "team_id": teams,
        "workload_type": "training-derived",
        "region": "azure-eastus-comparator",
        "priority_tier": "batch-synthetic",
        "min_spare_capacity_pct": 0.0,
        "interruptible_allowed": True,
    })
    return {"inventory": inventory, "usage": usage, "billing": billing, "sla": sla}, price


def _write_case(folder: Path, tables: dict, benchmark: dict, fault: str | None = None):
    folder.mkdir(parents=True, exist_ok=True)
    for role, frame in tables.items():
        _write(frame, folder / f"{role}.csv")
    details = {**benchmark, "fault_injection": fault}
    (folder / "benchmark.json").write_text(json.dumps(details, ensure_ascii=False, indent=2), encoding="utf-8")


def prepare_validation_cases(source: Path, output_root: Path):
    tables, price = _normal_tables(source)
    billing = tables["billing"]
    usage = tables["usage"]
    benchmark = {
        "input_rows": {name: len(frame) for name, frame in tables.items()},
        "gpu_count": float(tables["inventory"]["gpu_count"].sum()),
        "billed_gpu_hours": float(billing["billed_gpu_hours"].sum()),
        "total_cost_usd": float(billing["net_cost_usd"].sum()),
        "median_gpu_utilization_pct": float(usage["gpu_utilization_pct"].median()),
        "p95_gpu_utilization_pct": float(usage["gpu_utilization_pct"].quantile(.95)),
        "price_evidence": "Azure public Linux on-demand retail comparator",
        "price_query_date": "2026-09-14",
        "price_region": price["armRegionName"],
        "price_sku": price["armSkuName"],
        "source_gpu_utilization": "Alibaba PAI observed lifetime average",
        "limitations": [
            "Azure retail comparator is not Alibaba cost or a customer negotiated bill.",
            "Team, workload, region and SLA semantics are derived or synthetic.",
            "Alibaba timestamps are anonymized; dates are deterministically rebased while durations are preserved.",
            "GPU memory is published in GB without a reliable capacity denominator, so memory utilization remains missing.",
        ],
    }
    normal = output_root / "normal"
    _write_case(normal, tables, benchmark)

    blocked_tables = {name: frame.copy() for name, frame in tables.items()}
    blocked_tables["inventory"] = blocked_tables["inventory"].drop(columns="gpu_model")
    blocked = output_root / "blocked"
    _write_case(blocked, blocked_tables, benchmark, "required inventory.gpu_model removed")

    missing_tables = {name: frame.copy() for name, frame in tables.items()}
    first = missing_tables["usage"].index[0]
    missing_tables["usage"].loc[first, "gpu_utilization_pct"] = pd.NA
    missing_tables["usage"].loc[first, "active_gpu_count"] = pd.NA
    missing_tables["usage"].loc[first, "telemetry_status"] = "missing"
    missing = output_root / "missing-telemetry"
    _write_case(missing, missing_tables, benchmark, "one observed utilization value removed; missing retained as null")
    return {"normal": normal, "blocked": blocked, "missing_telemetry": missing}
