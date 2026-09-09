"""网页流程的纯逻辑契约。"""

import pandas as pd

from src.schema import TABLE_SPECS


def ready_for_audit(mapped_tables: dict, mapping_errors: dict) -> bool:
    return set(mapped_tables) == set(TABLE_SPECS) and not any(mapping_errors.values())


def ready_for_analysis(audit_result: pd.DataFrame) -> bool:
    if audit_result.empty or not {"severity", "status"}.issubset(audit_result.columns):
        return False
    blocking = audit_result["severity"].eq("阻断") & audit_result["status"].eq("异常")
    return not blocking.any()
