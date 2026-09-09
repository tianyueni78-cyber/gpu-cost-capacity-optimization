"""客户数据接入所使用的标准字段定义。"""

from dataclasses import dataclass


@dataclass(frozen=True)
class TableSpec:
    role: str
    label_zh: str
    key_field: str
    required_fields: tuple[str, ...]
    optional_fields: tuple[str, ...]
    field_labels: dict[str, str]


TABLE_SPECS = {
    "inventory": TableSpec(
        role="inventory",
        label_zh="GPU 资源清单",
        key_field="resource_pool_id",
        required_fields=(
            "resource_pool_id", "team_id", "gpu_model", "gpu_count", "region",
            "procurement_model", "effective_hourly_rate_usd",
        ),
        optional_fields=("product_id", "workload_type", "contract_id", "start_date", "end_date"),
        field_labels={
            "resource_pool_id": "资源池编号", "team_id": "团队编号", "gpu_model": "GPU 型号",
            "gpu_count": "GPU 数量", "region": "区域", "procurement_model": "采购方式",
            "effective_hourly_rate_usd": "有效小时费率（美元）", "product_id": "产品编号",
            "workload_type": "负载类型", "contract_id": "合同编号", "start_date": "启用日期",
            "end_date": "结束日期",
        },
    ),
    "usage": TableSpec(
        role="usage",
        label_zh="GPU 使用记录",
        key_field="usage_record_id",
        required_fields=(
            "usage_record_id", "timestamp_utc", "resource_pool_id", "allocated_gpu_count",
            "active_gpu_count", "gpu_utilization_pct",
        ),
        optional_fields=(
            "team_id", "product_id", "workload_type", "memory_utilization_pct",
            "business_volume", "volume_unit", "p95_latency_ms", "queue_time_seconds",
            "availability_pct", "telemetry_status",
        ),
        field_labels={
            "usage_record_id": "使用记录编号", "timestamp_utc": "UTC 时间", "resource_pool_id": "资源池编号",
            "allocated_gpu_count": "已分配 GPU 数", "active_gpu_count": "活跃 GPU 数",
            "gpu_utilization_pct": "GPU 利用率（%）", "team_id": "团队编号", "product_id": "产品编号",
            "workload_type": "负载类型", "memory_utilization_pct": "显存利用率（%）",
            "business_volume": "业务量", "volume_unit": "业务量单位", "p95_latency_ms": "P95 延迟（毫秒）",
            "queue_time_seconds": "排队时间（秒）", "availability_pct": "可用性（%）",
            "telemetry_status": "遥测状态",
        },
    ),
    "billing": TableSpec(
        role="billing",
        label_zh="GPU 云账单",
        key_field="billing_line_id",
        required_fields=(
            "billing_line_id", "invoice_month", "resource_pool_id", "charge_type",
            "procurement_model", "gross_cost_usd", "discount_usd", "net_cost_usd",
        ),
        optional_fields=(
            "team_id", "contract_id", "usage_start_date", "usage_end_date",
            "billed_gpu_hours", "unit_rate_usd", "currency",
        ),
        field_labels={
            "billing_line_id": "账单行编号", "invoice_month": "发票月份", "resource_pool_id": "资源池编号",
            "charge_type": "费用类型", "procurement_model": "采购方式", "gross_cost_usd": "原始费用（美元）",
            "discount_usd": "折扣（美元）", "net_cost_usd": "净成本（美元）", "team_id": "团队编号",
            "contract_id": "合同编号", "usage_start_date": "使用开始日期", "usage_end_date": "使用结束日期",
            "billed_gpu_hours": "计费 GPU 小时", "unit_rate_usd": "单位费率（美元）", "currency": "币种",
        },
    ),
    "sla": TableSpec(
        role="sla",
        label_zh="团队 SLA",
        key_field="sla_id",
        required_fields=(
            "sla_id", "team_id", "workload_type", "region", "priority_tier",
            "min_spare_capacity_pct",
        ),
        optional_fields=(
            "product_id", "effective_from", "effective_to", "availability_target_pct",
            "p95_latency_target_ms", "max_queue_time_seconds", "interruptible_allowed",
        ),
        field_labels={
            "sla_id": "SLA 编号", "team_id": "团队编号", "workload_type": "负载类型", "region": "区域",
            "priority_tier": "优先级", "min_spare_capacity_pct": "最低备用容量（%）", "product_id": "产品编号",
            "effective_from": "生效日期", "effective_to": "失效日期",
            "availability_target_pct": "可用性目标（%）", "p95_latency_target_ms": "P95 延迟目标（毫秒）",
            "max_queue_time_seconds": "最大排队时间（秒）", "interruptible_allowed": "是否允许中断",
        },
    ),
}
