from .comparability import ComparabilityResult


def can_verify(comparability: ComparabilityResult) -> bool:
    return comparability.allowed and not comparability.blocking_reasons


def persist_then_export(result, save, export) -> bytes:
    save(result)
    return export(result)
