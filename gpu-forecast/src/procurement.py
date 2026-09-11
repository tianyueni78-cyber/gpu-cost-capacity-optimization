from dataclasses import dataclass
from datetime import timedelta

import pandas as pd


@dataclass(frozen=True)
class PurchasePlanResult:
    rows: pd.DataFrame

    def optimize_actions(self):
        columns = [
            "team_id", "gpu_model", "region", "quantity", "effective_date",
            "procurement_method", "budget", "evidence_grade", "approval_status",
        ]
        return self.rows.reindex(columns=columns).copy()


def build_purchase_plan(scenarios, commercial_rules, approval_buffer_days):
    keys = ["gpu_model", "region"]
    rows = scenarios.loc[scenarios["shortfall_gpu_count"] > 0].merge(
        commercial_rules, on=keys, how="left", validate="many_to_one"
    )
    results = []
    for row in rows.to_dict("records"):
        effective_date = pd.Timestamp(row["period"]).date()
        grade = row.get("evidence_grade", "UNVERIFIABLE")
        has_rule = pd.notna(row.get("lead_days"))
        valid_price = has_rule and pd.Timestamp(row["valid_from"]).date() <= effective_date <= pd.Timestamp(row["valid_to"]).date()
        if not has_rule or not valid_price or grade == "UNVERIFIABLE":
            status = "BLOCKED"
        elif grade == "LOW":
            status = "OBSERVATION_ONLY"
        else:
            status = "PUBLISHABLE"
        quantity = int(row["shortfall_gpu_count"])
        budget = quantity * float(row["effective_rate"]) * int(row["billing_periods"]) if valid_price else float("nan")
        lead_days = int(row["lead_days"]) if has_rule else 0
        quota = int(row.get("quota_gpu_count", 0))
        risks = []
        if quantity > quota:
            risks.append("采购数量超过当前配额")
        if not valid_price:
            risks.append("价格有效期不覆盖生效日期")
        results.append({
            "team_id": row["team_id"], "gpu_model": row["gpu_model"], "region": row["region"],
            "shortfall_date": effective_date, "quantity": quantity,
            "latest_decision_date": effective_date - timedelta(days=lead_days + approval_buffer_days),
            "effective_date": effective_date, "procurement_method": row.get("procurement_method"),
            "budget": budget, "evidence_grade": grade, "risks": "；".join(risks) or "无已识别风险",
            "recommendation_status": status, "approval_status": "PENDING" if status == "PUBLISHABLE" else "NOT_READY",
        })
    return PurchasePlanResult(pd.DataFrame(results))
