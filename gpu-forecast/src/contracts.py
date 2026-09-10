from dataclasses import dataclass

import pandas as pd


@dataclass(frozen=True)
class ForecastScope:
    team_ids: tuple[str, ...]
    gpu_models: tuple[str, ...]
    regions: tuple[str, ...]
    period_start: str
    period_end: str
    frequency: str = "MS"
    min_history_periods: int = 12


@dataclass(frozen=True)
class ReadinessIssue:
    rule: str
    severity: str
    scope: str
    impact: str
    recommendation: str


@dataclass(frozen=True)
class ReadinessResult:
    allowed: bool
    evidence_grade: str
    blocking_reasons: tuple[str, ...]
    warnings: tuple[str, ...]
    coverage: dict[str, float]
    issues: tuple[ReadinessIssue, ...] = ()


@dataclass(frozen=True)
class ForecastInputs:
    business_history: pd.DataFrame
    resource_inventory: pd.DataFrame
    capacity_rules: pd.DataFrame
