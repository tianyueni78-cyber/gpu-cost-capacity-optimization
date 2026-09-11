def can_publish_purchase_plan(evidence_grade):
    return evidence_grade in {"HIGH", "MEDIUM"}


def dataframe_csv(frame):
    return frame.to_csv(index=False).encode("utf-8-sig")


def management_summary(percentile, bias, shortfall, budget, risks):
    return (
        "# GPU Forecast 管理摘要\n\n"
        f"- 容量口径：{percentile}\n"
        f"- 回测偏差：{bias}\n"
        f"- GPU 缺口：{shortfall}\n"
        f"- 预算：{budget}\n"
        f"- 主要风险：{risks}\n"
    )
