import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd


GPU_DATA_ROOT = Path(__file__).parents[2] / "gpu-data"
if str(GPU_DATA_ROOT) not in sys.path:
    sys.path.insert(0, str(GPU_DATA_ROOT))

from src.audit import AUDIT_COLUMNS, audit_tables  # noqa: E402
from src.baseline import build_baseline  # noqa: E402
from src.intake import apply_mapping, read_csv_bytes, suggest_mapping, validate_mapping  # noqa: E402
from src.public_validation import prepare_validation_cases  # noqa: E402
from src.reporting import build_csv_exports, build_markdown_report  # noqa: E402
from src.schema import TABLE_SPECS  # noqa: E402
from src.signals import build_investigation_signals  # noqa: E402
from src.workflow import ready_for_analysis  # noqa: E402


def _records(frame):
    return json.loads(frame.to_json(orient="records", date_format="iso"))


def _write_csv(frame, path):
    path.write_bytes(frame.to_csv(index=False).encode("utf-8-sig"))


def inspect_files(files: dict[str, tuple[str, bytes]]):
    frames = {role: read_csv_bytes(content) for role, (_name, content) in files.items()}
    usage = frames["usage"]
    timestamp_column = suggest_mapping(usage.columns, TABLE_SPECS["usage"]).get("timestamp_utc")
    timestamps = pd.to_datetime(usage[timestamp_column], errors="coerce", utc=True) if timestamp_column else pd.Series(dtype="datetime64[ns, UTC]")
    valid = timestamps.dropna()
    return {
        "row_counts": {role: len(frame) for role, frame in frames.items()},
        "period_start": valid.min().isoformat() if not valid.empty else None,
        "period_end": valid.max().isoformat() if not valid.empty else None,
    }


def prepare_public_files(source_root: Path, output_root: Path):
    normal = prepare_validation_cases(source_root, output_root)["normal"]
    return {role: (f"{role}.csv", (normal / f"{role}.csv").read_bytes()) for role in TABLE_SPECS}


def run_analysis(source_dir: Path, output_dir: Path):
    output_dir.mkdir(parents=True, exist_ok=True)
    tables = {}
    mapping_findings = []
    for role, spec in TABLE_SPECS.items():
        frame = read_csv_bytes((source_dir / f"{role}.csv").read_bytes())
        mapping = suggest_mapping(frame.columns, spec)
        errors = validate_mapping(mapping, spec)
        if errors:
            mapping_findings.append({
                "check_id": f"{role}.field_mapping",
                "table_name": role,
                "category": "字段映射",
                "severity": "阻断",
                "status": "异常",
                "affected_rows": len(frame),
                "total_rows": len(frame),
                "message": "；".join(errors),
                "action": "补齐必填字段或修正字段名称后重新上传。",
            })
        else:
            tables[role] = apply_mapping(frame, mapping)

    audit = pd.DataFrame(mapping_findings, columns=AUDIT_COLUMNS) if mapping_findings else audit_tables(tables)
    blocking_count = int((audit["severity"].eq("阻断") & audit["status"].eq("异常")).sum())
    warning_count = int((audit["severity"].eq("警告") & audit["status"].eq("异常")).sum())
    quality_path = output_dir / "data_quality.csv"
    _write_csv(audit.reindex(columns=AUDIT_COLUMNS), quality_path)
    if not ready_for_analysis(audit):
        return {
            "status": "BLOCKED",
            "summary": {"blocking_count": blocking_count, "warning_count": warning_count},
            "audit": _records(audit),
            "signals": [],
            "artifacts": [{"kind": "data_quality", "path": str(quality_path), "mime_type": "text/csv"}],
        }

    baseline = build_baseline(tables)
    signals = build_investigation_signals(tables, baseline)
    coverage = baseline["coverage"].iloc[0]
    cost = baseline["cost_summary"].iloc[0]
    capacity = baseline["capacity_summary"].iloc[0]
    usage = baseline["usage_distribution"].iloc[0]
    idle = signals[signals["signal_type"].isin(("high_cost_low_activity", "allocated_active_gap"))].drop_duplicates("scope")
    period = f"{pd.to_datetime(coverage['usage_start_utc']).date()} 至 {pd.to_datetime(coverage['usage_end_utc']).date()}"
    exports = build_csv_exports(baseline, signals, audit)
    report_path = output_dir / "report.md"
    report_path.write_text(build_markdown_report(baseline, signals, audit, {
        "analysis_period": period,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }), encoding="utf-8")
    idle_path = output_dir / "idle_candidates.csv"
    _write_csv(idle, idle_path)
    allocation_path = output_dir / "cost_allocation.csv"
    _write_csv(baseline["cost_breakdown"], allocation_path)
    quality_path.write_bytes(exports["data_quality.csv"])
    summary = {
        "total_cost_usd": float(cost["net_cost_usd"]),
        "attributed_cost_usd": float(cost["net_cost_usd"] - coverage["unassigned_net_cost_usd"]),
        "unattributed_cost_usd": float(coverage["unassigned_net_cost_usd"]),
        "cost_attribution_coverage_pct": float(coverage["cost_attribution_coverage_pct"]),
        "gpu_count": float(capacity["inventory_gpu_count"]),
        "gpu_telemetry_coverage_pct": float(coverage["gpu_telemetry_coverage_pct"]),
        "median_gpu_utilization_pct": float(usage["median_gpu_utilization_pct"]),
        "p95_gpu_utilization_pct": float(usage["p95_gpu_utilization_pct"]),
        "idle_candidate_count": len(idle),
        "idle_affected_cost_usd": float(idle["affected_cost_usd"].sum()),
        "blocking_count": blocking_count,
        "warning_count": warning_count,
        "analysis_period": period,
        "currency": "USD",
        "source": "GPU Data CSV",
        "inventory_by_model": _records(tables["inventory"].groupby("gpu_model", as_index=False)["gpu_count"].sum()),
        "inventory_by_team": _records(tables["inventory"].groupby("team_id", as_index=False)["gpu_count"].sum()),
    }
    return {
        "status": "SUCCEEDED",
        "summary": summary,
        "audit": _records(audit),
        "signals": _records(signals),
        "artifacts": [
            {"kind": "report", "path": str(report_path), "mime_type": "text/markdown"},
            {"kind": "idle_candidates", "path": str(idle_path), "mime_type": "text/csv"},
            {"kind": "data_quality", "path": str(quality_path), "mime_type": "text/csv"},
            {"kind": "cost_allocation", "path": str(allocation_path), "mime_type": "text/csv"},
        ],
    }
