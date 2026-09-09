"""网页流程的纯逻辑契约。"""

from src.schema import TABLE_SPECS


def ready_for_audit(mapped_tables: dict, mapping_errors: dict) -> bool:
    return set(mapped_tables) == set(TABLE_SPECS) and not any(mapping_errors.values())

