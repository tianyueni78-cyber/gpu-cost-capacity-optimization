import csv
from datetime import date
from io import StringIO
from typing import BinaryIO, TextIO

from .models import ActionRecord, ActionType, ImportErrorDetail, ImportResult


REQUIRED_FIELDS = (
    "action_id",
    "action_type",
    "resource_pool_id",
    "owner",
    "approved_at",
    "planned_execution_at",
    "estimated_savings_usd",
    "implementation_cost_usd",
)


def _read_text(file: BinaryIO | TextIO) -> str:
    value = file.read()
    if isinstance(value, bytes):
        return value.decode("utf-8-sig")
    return value


def validate_action_row(row: dict[str, str], row_number: int) -> list[ImportErrorDetail]:
    errors = [
        ImportErrorDetail(row_number, field, "该字段不能为空")
        for field in REQUIRED_FIELDS
        if not str(row.get(field, "")).strip()
    ]
    if errors:
        return errors

    try:
        ActionType(row["action_type"].strip())
    except ValueError:
        errors.append(ImportErrorDetail(row_number, "action_type", "不支持的行动类型"))

    for field in ("approved_at", "planned_execution_at"):
        try:
            date.fromisoformat(row[field].strip())
        except ValueError:
            errors.append(ImportErrorDetail(row_number, field, "日期必须使用 YYYY-MM-DD"))

    for field in ("estimated_savings_usd", "implementation_cost_usd"):
        try:
            if float(row[field]) < 0:
                raise ValueError
        except ValueError:
            errors.append(ImportErrorDetail(row_number, field, "金额必须是大于等于零的数字"))
    return errors


def read_actions_csv(file: BinaryIO | TextIO) -> ImportResult:
    reader = csv.DictReader(StringIO(_read_text(file)))
    records: list[ActionRecord] = []
    errors: list[ImportErrorDetail] = []

    missing_columns = [field for field in REQUIRED_FIELDS if field not in (reader.fieldnames or [])]
    if missing_columns:
        return ImportResult(
            (),
            tuple(ImportErrorDetail(1, field, "CSV 缺少必需列") for field in missing_columns),
        )

    for row_number, row in enumerate(reader, start=2):
        row_errors = validate_action_row(row, row_number)
        if row_errors:
            errors.extend(row_errors)
            continue
        records.append(
            ActionRecord(
                action_id=row["action_id"].strip(),
                action_type=ActionType(row["action_type"].strip()),
                resource_pool_id=row["resource_pool_id"].strip(),
                owner=row["owner"].strip(),
                approved_at=date.fromisoformat(row["approved_at"].strip()),
                planned_execution_at=date.fromisoformat(row["planned_execution_at"].strip()),
                estimated_savings_usd=float(row["estimated_savings_usd"]),
                implementation_cost_usd=float(row["implementation_cost_usd"]),
            )
        )
    return ImportResult(tuple(records), tuple(errors))
