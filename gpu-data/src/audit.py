"""透明、只读的数据质量审计规则。"""

import re

import pandas as pd

from src.schema import TABLE_SPECS


AUDIT_COLUMNS = [
    "check_id", "table_name", "category", "severity", "status",
    "affected_rows", "total_rows", "message", "action",
]

ALLOWED_PROCUREMENT_MODELS = {
    "ondemand", "reserved", "savingsplan", "spot", "owned",
}


def _normalise_id(series: pd.Series) -> pd.Series:
    return series.astype("string").str.strip().str.upper().str.replace(r"[^A-Z0-9]", "", regex=True)


def _exact_id(series: pd.Series) -> pd.Series:
    return series.astype("string").str.strip().str.upper()


def _finding(check_id, table_name, category, severity, affected_rows, total_rows, message, action):
    affected_rows = int(affected_rows)
    return {
        "check_id": check_id,
        "table_name": table_name,
        "category": category,
        "severity": severity,
        "status": "异常" if affected_rows else "通过",
        "affected_rows": affected_rows,
        "total_rows": int(total_rows),
        "message": message,
        "action": action,
    }


def _missing_mask(frame: pd.DataFrame, fields) -> pd.Series:
    mask = pd.Series(False, index=frame.index)
    for field in fields:
        if field not in frame:
            mask |= True
        else:
            values = frame[field]
            mask |= values.isna() | values.astype("string").str.strip().eq("").fillna(False)
    return mask


def _numeric(frame, field):
    return pd.to_numeric(frame[field], errors="coerce")


def audit_tables(tables: dict[str, pd.DataFrame]) -> pd.DataFrame:
    findings = []
    required_value_fields = {
        "inventory": TABLE_SPECS["inventory"].required_fields,
        "usage": ("usage_record_id", "timestamp_utc", "resource_pool_id", "allocated_gpu_count", "active_gpu_count"),
        "billing": (
            "billing_line_id", "invoice_month", "charge_type", "procurement_model",
            "gross_cost_usd", "discount_usd", "net_cost_usd",
        ),
        "sla": TABLE_SPECS["sla"].required_fields,
    }

    for role, spec in TABLE_SPECS.items():
        frame = tables.get(role, pd.DataFrame())
        total = len(frame)
        findings.append(_finding(
            f"{role}.table_not_empty", role, "完整性", "阻断", int(total == 0), total,
            "文件应至少包含一条记录。", "检查是否上传了正确文件，并确认导出范围。",
        ))
        if total == 0:
            continue

        duplicate_rows = (
            frame[spec.key_field].duplicated(keep=False).sum()
            if spec.key_field in frame else total
        )
        findings.append(_finding(
            f"{role}.unique_key", role, "重复", "阻断", duplicate_rows, total,
            f"候选主键 {spec.key_field} 应保持唯一。", "定位重复键，区分完全重复与修订记录后再制定保留规则。",
        ))
        required_missing = _missing_mask(frame, required_value_fields[role]).sum()
        findings.append(_finding(
            f"{role}.required_values", role, "空值", "阻断", required_missing, total,
            "每行的必填业务字段都应有值。", "回到数据源补齐，或确认字段是否确实不适用；不要直接填零。",
        ))

    inventory = tables.get("inventory", pd.DataFrame())
    if not inventory.empty:
        gpu_count = _numeric(inventory, "gpu_count")
        rate = _numeric(inventory, "effective_hourly_rate_usd")
        findings.extend([
            _finding(
                "inventory.gpu_count_positive", "inventory", "范围", "阻断",
                (gpu_count.isna() | gpu_count.le(0)).sum(), len(inventory),
                "GPU 数量必须是大于 0 的数值。", "核对数量单位和导出格式。",
            ),
            _finding(
                "inventory.hourly_rate_non_negative", "inventory", "范围", "阻断",
                (rate.isna() | rate.lt(0)).sum(), len(inventory),
                "有效小时费率必须是大于等于 0 的数值。", "核对币种、单位及自有资源的计价口径。",
            ),
        ])
        procurement = inventory["procurement_model"].astype("string").map(
            lambda value: re.sub(r"[^a-z]", "", str(value).lower())
        )
        findings.append(_finding(
            "inventory.procurement_enum", "inventory", "枚举", "警告",
            (~procurement.isin(ALLOWED_PROCUREMENT_MODELS)).sum(), len(inventory),
            "采购方式应能映射到按需、预留、节省计划、竞价或自有资源。",
            "确认云厂商术语并补充显式映射，不要静默归类。",
        ))

    usage = tables.get("usage", pd.DataFrame())
    if not usage.empty:
        allocated = _numeric(usage, "allocated_gpu_count")
        active = _numeric(usage, "active_gpu_count")
        utilisation = _numeric(usage, "gpu_utilization_pct")
        timestamps = pd.to_datetime(usage["timestamp_utc"], errors="coerce", utc=True)
        business_keys = pd.DataFrame({
            "timestamp": timestamps,
            "resource_pool_id": _normalise_id(usage["resource_pool_id"]),
        })
        complete_key = business_keys.notna().all(axis=1)
        duplicated_business_rows = complete_key & business_keys.duplicated(keep=False)
        findings.extend([
            _finding(
                "usage.business_key_duplicate", "usage", "重复", "阻断",
                duplicated_business_rows.sum(), len(usage),
                "同一资源池在同一采集时点应只有一个有效版本。",
                "区分完全重复与修订记录，并依据明确版本字段保留有效记录。",
            ),
            _finding(
                "usage.active_not_above_allocated", "usage", "范围", "阻断",
                (active.gt(allocated) | active.lt(0) | allocated.lt(0)).sum(), len(usage),
                "活跃 GPU 数不能超过已分配数量，二者也不能为负。", "核对采集时点、数量单位和聚合粒度。",
            ),
            _finding(
                "usage.gpu_utilization_range", "usage", "范围", "阻断",
                (utilisation.notna() & ~utilisation.between(0, 100)).sum(), len(usage),
                "GPU 利用率应在 0% 到 100% 之间。", "核对百分比是否被重复乘以 100。",
            ),
            _finding(
                "usage.timestamp_format", "usage", "时间", "阻断",
                timestamps.isna().sum(), len(usage),
                "使用时间必须能解析为带时区的时间。", "统一时区与时间格式后重新导出。",
            ),
        ])
        for field in ("gpu_utilization_pct", "memory_utilization_pct", "p95_latency_ms", "queue_time_seconds", "availability_pct"):
            if field not in usage:
                continue
            missing_telemetry = usage[field].isna().sum()
            findings.append(_finding(
                f"usage.{field}_missing", "usage", "空值", "警告",
                missing_telemetry, len(usage),
                f"可选遥测字段 {field} 存在空值；空值不代表零。",
                "保留空值并结合负载类型、遥测状态判断是否排除或单独展示。",
            ))

    billing = tables.get("billing", pd.DataFrame())
    if not billing.empty:
        gross = _numeric(billing, "gross_cost_usd")
        discount = _numeric(billing, "discount_usd")
        net = _numeric(billing, "net_cost_usd")
        formula_invalid = gross.isna() | discount.isna() | net.isna() | ((gross - discount - net).abs() > 0.01)
        invoice_valid = billing["invoice_month"].astype("string").str.fullmatch(r"\d{4}-(0[1-9]|1[0-2])", na=False)
        billing_procurement = billing["procurement_model"].astype("string").map(
            lambda value: re.sub(r"[^a-z]", "", str(value).lower())
        )
        if "contract_id" in billing:
            missing_contract = billing["contract_id"].isna() | billing["contract_id"].astype("string").str.strip().eq("").fillna(False)
            committed_missing_contract = billing_procurement.isin({"reserved", "savingsplan"}) & missing_contract
        else:
            committed_missing_contract = billing_procurement.isin({"reserved", "savingsplan"})
        findings.extend([
            _finding(
                "billing.net_cost_formula", "billing", "金额", "阻断",
                formula_invalid.sum(), len(billing),
                "净成本应等于原始费用减去折扣，允许 0.01 美元舍入误差。", "按账单行定位差异并核对费用口径。",
            ),
            _finding(
                "billing.invoice_month_format", "billing", "时间", "阻断",
                (~invoice_valid).sum(), len(billing),
                "发票月份必须使用 YYYY-MM 格式。", "修正月份格式，并与使用期间分别保留。",
            ),
            _finding(
                "billing.procurement_enum", "billing", "枚举", "警告",
                (~billing_procurement.isin(ALLOWED_PROCUREMENT_MODELS)).sum(), len(billing),
                "账单采购方式应能映射到已确认的标准分类。", "核对云厂商术语并补充显式映射。",
            ),
            _finding(
                "billing.committed_contract", "billing", "条件完整性", "阻断",
                committed_missing_contract.sum(), len(billing),
                "预留采购和节省计划必须具有合同编号；按需、竞价和自有资源可为空。",
                "按采购方式拆分核对合同字段，不要给不适用记录强行填值。",
            ),
        ])

    sla = tables.get("sla", pd.DataFrame())
    if not sla.empty:
        spare = _numeric(sla, "min_spare_capacity_pct")
        findings.append(_finding(
            "sla.spare_capacity_range", "sla", "范围", "阻断",
            (spare.isna() | ~spare.between(0, 100)).sum(), len(sla),
            "最低备用容量应在 0% 到 100% 之间。", "核对百分比单位和 SLA 原文。",
        ))

    if not inventory.empty:
        inventory_exact_ids = set(_exact_id(inventory["resource_pool_id"]).dropna())
        inventory_ids = set(_normalise_id(inventory["resource_pool_id"]).dropna())
        for role in ("usage", "billing"):
            frame = tables.get(role, pd.DataFrame())
            if frame.empty:
                continue
            exact_ids = _exact_id(frame["resource_pool_id"])
            normalised_ids = _normalise_id(frame["resource_pool_id"])
            exact_unmatched = exact_ids.notna() & ~exact_ids.isin(inventory_exact_ids)
            normalised_unmatched = normalised_ids.notna() & ~normalised_ids.isin(inventory_ids)
            findings.extend([
                _finding(
                    f"{role}.pool_linkage_exact", role, "关联", "警告",
                    exact_unmatched.sum(), len(frame),
                    "资源池编号按原始格式关联时存在未匹配记录。", "比较大小写和分隔符，确认标准化规则不会合并不同 ID。",
                ),
                _finding(
                    f"{role}.pool_linkage_normalized", role, "关联", "阻断",
                    normalised_unmatched.sum(), len(frame),
                    "资源池编号标准化后仍应能关联到 GPU 资源清单。", "补齐缺失资源池或更正编号；关联前后必须对账。",
                ),
            ])

    return pd.DataFrame(findings, columns=AUDIT_COLUMNS)
