import pandas as pd


def run_demo_portfolio():
    rows = pd.DataFrame([
        {"scope": "搜索推理 / H100 / cn-east-1", "evidence_grade": "HIGH", "decision_status": "PUBLISHABLE", "planned_gpu_count": 12},
        {"scope": "训练 / A100 / cn-east-1", "evidence_grade": "LOW", "decision_status": "OBSERVATION_ONLY", "planned_gpu_count": 6},
        {"scope": "文档推理 / L40S / cn-south-1", "evidence_grade": "UNVERIFIABLE", "decision_status": "UNVERIFIABLE", "planned_gpu_count": 0},
    ])
    rows.attrs["total_planned_gpu_count"] = int(rows["planned_gpu_count"].sum())
    return rows
