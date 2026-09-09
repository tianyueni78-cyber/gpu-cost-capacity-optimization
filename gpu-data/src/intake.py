"""CSV 读取与用户确认式字段映射。"""

from io import StringIO
import re

import pandas as pd

from src.schema import TableSpec


class DataInputError(ValueError):
    """客户上传文件无法安全读取。"""


ALIASES = {
    "resource_pool_id": ("资源池", "资源池编号", "gpu_pool_id", "pool_id"),
    "team_id": ("团队", "团队编号", "department_id"),
    "product_id": ("产品", "产品编号"),
    "workload_type": ("负载类型", "任务类型"),
    "gpu_model": ("gpu型号", "显卡型号"),
    "gpu_count": ("gpu数量", "显卡数量", "卡数"),
    "region": ("区域", "地域"),
    "procurement_model": ("采购方式", "计费方式"),
    "contract_id": ("合同编号", "合约编号"),
    "start_date": ("启用日期", "开始日期"),
    "end_date": ("结束日期", "失效日期"),
    "effective_hourly_rate_usd": ("有效小时费率", "实际小时费率"),
    "usage_record_id": ("使用记录编号", "用量记录编号"),
    "timestamp_utc": ("utc时间", "使用时间", "采集时间"),
    "allocated_gpu_count": ("已分配gpu数", "分配gpu数量"),
    "active_gpu_count": ("活跃gpu数", "使用gpu数量"),
    "gpu_utilization_pct": ("gpu利用率", "gpu使用率"),
    "memory_utilization_pct": ("显存利用率", "内存利用率"),
    "business_volume": ("业务量",),
    "volume_unit": ("业务量单位",),
    "p95_latency_ms": ("p95延迟", "p95延迟毫秒"),
    "queue_time_seconds": ("排队时间", "排队秒数"),
    "availability_pct": ("可用性", "可用率"),
    "telemetry_status": ("遥测状态", "采集状态"),
    "billing_line_id": ("账单行编号", "账单记录编号"),
    "invoice_month": ("发票月份", "账单月份"),
    "charge_type": ("费用类型",),
    "gross_cost_usd": ("原始费用", "折扣前费用"),
    "discount_usd": ("折扣", "折扣金额"),
    "net_cost_usd": ("净成本", "实际费用"),
    "usage_start_date": ("使用开始日期",),
    "usage_end_date": ("使用结束日期",),
    "billed_gpu_hours": ("计费gpu小时",),
    "unit_rate_usd": ("单位费率",),
    "currency": ("币种", "货币"),
    "sla_id": ("sla编号", "服务等级编号"),
    "priority_tier": ("优先级", "sla等级"),
    "min_spare_capacity_pct": ("最低备用容量", "最小冗余容量"),
    "effective_from": ("生效日期",),
    "effective_to": ("失效日期",),
    "availability_target_pct": ("可用性目标",),
    "p95_latency_target_ms": ("p95延迟目标",),
    "max_queue_time_seconds": ("最大排队时间",),
    "interruptible_allowed": ("是否允许中断",),
}


def _normalise_name(value: str) -> str:
    return re.sub(r"[^0-9a-z\u4e00-\u9fff]+", "", str(value).strip().lower())


def read_csv_bytes(content: bytes) -> pd.DataFrame:
    if not content:
        raise DataInputError("空文件无法读取")
    for encoding in ("utf-8-sig", "gb18030"):
        try:
            text = content.decode(encoding)
            frame = pd.read_csv(StringIO(text))
            if frame.columns.empty:
                raise DataInputError("CSV 没有字段")
            return frame
        except UnicodeDecodeError:
            continue
        except pd.errors.EmptyDataError as exc:
            raise DataInputError("空文件无法读取") from exc
        except pd.errors.ParserError as exc:
            raise DataInputError(f"CSV 格式错误：{exc}") from exc
    raise DataInputError("无法识别文件编码，请另存为 UTF-8 或 GB18030")


def suggest_mapping(columns, spec: TableSpec) -> dict[str, str | None]:
    normalised_columns = {_normalise_name(column): column for column in columns}
    suggestions = {}
    for field in spec.required_fields + spec.optional_fields:
        candidates = (field,) + ALIASES.get(field, ())
        suggestions[field] = next(
            (normalised_columns[_normalise_name(name)] for name in candidates if _normalise_name(name) in normalised_columns),
            None,
        )
    return suggestions


def validate_mapping(mapping: dict[str, str | None], spec: TableSpec) -> list[str]:
    errors = []
    missing = [spec.field_labels[field] for field in spec.required_fields if not mapping.get(field)]
    if missing:
        errors.append(f"必填字段尚未映射：{'、'.join(missing)}")
    selected = [source for source in mapping.values() if source]
    duplicated = sorted({source for source in selected if selected.count(source) > 1})
    if duplicated:
        errors.append(f"源字段被重复使用：{'、'.join(duplicated)}")
    return errors


def apply_mapping(frame: pd.DataFrame, mapping: dict[str, str | None]) -> pd.DataFrame:
    selected = {source: canonical for canonical, source in mapping.items() if source}
    return frame.loc[:, list(selected)].rename(columns=selected).copy()
