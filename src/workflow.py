"""网页流程的纯逻辑契约。"""

from src.schema import TABLE_SPECS


def ready_for_audit(mapped_tables: dict, mapping_errors: dict) -> bool:
    return set(mapped_tables) == set(TABLE_SPECS) and not any(mapping_errors.values())


def ready_for_optimization(audit_result, constraints_confirmed: bool) -> bool:
    if audit_result is None or audit_result.empty or not constraints_confirmed:
        return False
    blocking = audit_result["status"].eq("异常") & audit_result["severity"].eq("阻断")
    return not blocking.any()
