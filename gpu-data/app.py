"""GPU Data：本地 CSV 接入、现状分析、调查线索与诊断导出。"""

import pandas as pd
import streamlit as st

from src.audit import audit_tables
from src.baseline import build_baseline
from src.intake import DataInputError, apply_mapping, read_csv_bytes, suggest_mapping, validate_mapping
from src.reporting import build_csv_exports, build_markdown_report
from src.schema import TABLE_SPECS
from src.signals import build_investigation_signals
from src.workflow import ready_for_analysis, ready_for_audit


PAGE_NAMES = ("数据接入", "当前状况", "调查线索", "诊断报告")


def _analysis_context():
    audit_result = st.session_state.get("audit_result")
    mapped_tables = st.session_state.get("mapped_tables")
    if audit_result is None or mapped_tables is None:
        st.info("请先完成数据接入并通过审计，再查看本页。")
        return None
    if not ready_for_analysis(audit_result):
        st.error("数据审计仍有阻断项。修复数据并重新运行审计后才能生成分析结果。")
        return None
    baseline = build_baseline(mapped_tables)
    signals = build_investigation_signals(mapped_tables, baseline)
    return mapped_tables, audit_result, baseline, signals


def _metric_value(value, prefix="", suffix=""):
    if pd.isna(value):
        return "数据不足"
    if isinstance(value, (int, float)):
        return f"{prefix}{float(value):,.2f}{suffix}"
    return str(value)


def render_data_intake():
    st.title("GPU Data")
    st.caption("发现资源与成本问题：先证明数据可信，再展示现状和调查线索。")
    st.info("上传文件仅保留在当前本地会话，不写入磁盘；产品不会修改源数据或生产资源。")

    st.header("1. 上传四类业务 CSV")
    st.write("每个入口对应一种业务角色，避免系统把账单误认成使用记录。")
    uploaded_frames = {}
    upload_columns = st.columns(2)
    for index, (role, spec) in enumerate(TABLE_SPECS.items()):
        with upload_columns[index % 2]:
            uploaded = st.file_uploader(
                spec.label_zh, type=["csv"], key=f"upload_{role}",
                help=f"上传 {spec.label_zh}，CSV 第一行必须是字段名。",
            )
            if uploaded is not None:
                try:
                    frame = read_csv_bytes(uploaded.getvalue())
                    uploaded_frames[role] = frame
                    st.success(f"已读取 {len(frame):,} 行 × {len(frame.columns)} 列")
                    st.dataframe(frame.head(3), use_container_width=True, hide_index=True)
                except DataInputError as exc:
                    st.error(str(exc))

    st.header("2. 确认字段映射")
    st.write("系统只提供建议。请确认客户字段与标准字段的对应关系；“*”表示必填。")
    mapped_tables = {}
    mapping_errors = {}
    for role, frame in uploaded_frames.items():
        spec = TABLE_SPECS[role]
        suggestions = suggest_mapping(frame.columns, spec)
        with st.expander(f"{spec.label_zh}字段映射", expanded=True):
            options = ["— 不映射 —"] + list(frame.columns)
            mapping = {}
            fields = spec.required_fields + spec.optional_fields
            rows = st.columns(2)
            for index, field in enumerate(fields):
                suggested = suggestions[field]
                default_index = options.index(suggested) if suggested in options else 0
                label = spec.field_labels[field] + (" *" if field in spec.required_fields else "")
                with rows[index % 2]:
                    selected = st.selectbox(
                        f"{label}  →  `{field}`", options, index=default_index,
                        key=f"mapping_{role}_{field}",
                    )
                    mapping[field] = None if selected == "— 不映射 —" else selected
            errors = validate_mapping(mapping, spec)
            mapping_errors[role] = errors
            if errors:
                for error in errors:
                    st.error(error)
            else:
                st.success("映射完整，可以进入审计。")
                mapped_tables[role] = apply_mapping(frame, mapping)

    st.header("3. 自动数据审计")
    is_ready = ready_for_audit(mapped_tables, mapping_errors)
    if not is_ready:
        st.caption("上传并完成四张表的必填字段映射后，审计按钮才会启用。")
    if st.button("运行自动审计", type="primary", disabled=not is_ready, use_container_width=True):
        st.session_state["mapped_tables"] = mapped_tables
        st.session_state["audit_result"] = audit_tables(mapped_tables)

    if "audit_result" not in st.session_state:
        return
    result = st.session_state["audit_result"]
    abnormal = result[result["status"].eq("异常")]
    metrics = st.columns(3)
    metrics[0].metric("通过", int(result["status"].eq("通过").sum()))
    metrics[1].metric("警告", int((result["status"].eq("异常") & result["severity"].eq("警告")).sum()))
    metrics[2].metric("阻断", int((result["status"].eq("异常") & result["severity"].eq("阻断")).sum()))
    if abnormal["severity"].eq("阻断").any():
        st.error("存在阻断项：修复或确认规则前，不应生成成本与资源结论。")
    elif not abnormal.empty:
        st.warning("没有阻断项，但警告项会保留在最终报告中。")
    else:
        st.success("当前规则范围内全部通过，可以查看当前状况。")
    display = result.copy()
    display["table_name"] = display["table_name"].map(
        {role: spec.label_zh for role, spec in TABLE_SPECS.items()}
    )
    st.dataframe(display, use_container_width=True, hide_index=True)
    st.download_button(
        "下载审计报告 CSV", result.to_csv(index=False).encode("utf-8-sig"),
        "gpu_data_audit_report.csv", "text/csv",
    )


def render_current_status():
    st.title("当前状况")
    st.caption("回答钱花在哪、资源如何使用，以及数据能支持哪些判断。")
    context = _analysis_context()
    if context is None:
        return
    _, _, baseline, _ = context
    costs = baseline["cost_summary"].iloc[0]
    capacity = baseline["capacity_summary"].iloc[0]
    usage = baseline["usage_distribution"].iloc[0]
    coverage = baseline["coverage"].iloc[0]

    st.subheader("成本概况")
    cost_metrics = st.columns(4)
    cost_metrics[0].metric("净成本", _metric_value(costs["net_cost_usd"], "$"))
    cost_metrics[1].metric("原始费用", _metric_value(costs["gross_cost_usd"], "$"))
    cost_metrics[2].metric("折扣", _metric_value(costs["discount_usd"], "$"))
    cost_metrics[3].metric("成本归属覆盖率", _metric_value(coverage["cost_attribution_coverage_pct"], suffix="%"))
    st.dataframe(baseline["cost_breakdown"], use_container_width=True, hide_index=True)

    st.subheader("资源与使用")
    resource_metrics = st.columns(4)
    resource_metrics[0].metric("库存 GPU", _metric_value(capacity["inventory_gpu_count"]))
    resource_metrics[1].metric("活跃 GPU 中位数", _metric_value(capacity["median_active_gpu_count"]))
    resource_metrics[2].metric("活跃 GPU P95", _metric_value(capacity["p95_active_gpu_count"]))
    resource_metrics[3].metric("活跃 GPU 峰值", _metric_value(capacity["peak_active_gpu_count"]))
    utilization_metrics = st.columns(4)
    utilization_metrics[0].metric("GPU 利用率中位数", _metric_value(usage["median_gpu_utilization_pct"], suffix="%"))
    utilization_metrics[1].metric("GPU 利用率 P95", _metric_value(usage["p95_gpu_utilization_pct"], suffix="%"))
    utilization_metrics[2].metric("显存利用率中位数", _metric_value(usage["median_memory_utilization_pct"], suffix="%"))
    utilization_metrics[3].metric("显存利用率 P95", _metric_value(usage["p95_memory_utilization_pct"], suffix="%"))

    st.subheader("数据与 SLA 覆盖")
    st.dataframe(baseline["coverage"], use_container_width=True, hide_index=True)
    st.dataframe(baseline["sla_summary"], use_container_width=True, hide_index=True)
    st.caption("以上利用率为观测事实；低利用率本身不代表资源可被回收。")


def render_signals():
    st.title("调查线索")
    st.caption("每条线索展示观察、证据、限制条件和需要负责人核对的问题。")
    context = _analysis_context()
    if context is None:
        return
    _, _, _, signals = context
    if signals.empty:
        st.success("当前规则和数据覆盖范围内未发现调查线索。")
        return
    priorities = ["全部"] + [value for value in ("高", "中", "低") if value in set(signals["priority"])]
    selected = st.selectbox("优先级", priorities)
    display = signals if selected == "全部" else signals[signals["priority"].eq(selected)]
    for _, signal in display.iterrows():
        with st.expander(f"{signal['priority']}｜{signal['scope']}｜{signal['observation']}"):
            st.write(f"**证据：** {signal['evidence']}")
            st.metric("相关成本（不是可节省金额）", f"${float(signal['affected_cost_usd']):,.2f}")
            st.write(f"**为什么不能直接下结论：** {signal['limitation']}")
            st.write(f"**需要核查：** {signal['question']}")
            st.caption(f"来源：{signal['source_tables']}｜期间：{signal['period']}｜记录：{signal['affected_rows']} 条")


def render_report():
    st.title("诊断报告")
    st.caption("导出可复核的管理摘要、指标明细、调查线索和数据质量结果。")
    context = _analysis_context()
    if context is None:
        return
    _, audit_result, baseline, signals = context
    coverage = baseline["coverage"].iloc[0]
    period = f"{coverage['usage_start_utc']} 至 {coverage['usage_end_utc']}"
    report = build_markdown_report(baseline, signals, audit_result, {"analysis_period": period})
    exports = build_csv_exports(baseline, signals, audit_result)
    st.markdown(report)
    st.download_button(
        "下载管理诊断报告", report.encode("utf-8"),
        "gpu_data_diagnostic_report.md", "text/markdown",
    )
    labels = {
        "metrics.csv": "下载指标明细 CSV",
        "signals.csv": "下载调查线索 CSV",
        "data_quality.csv": "下载数据质量 CSV",
    }
    for filename, content in exports.items():
        st.download_button(labels[filename], content, filename, "text/csv")


st.set_page_config(page_title="GPU Data", page_icon="📊", layout="wide")
page = st.sidebar.radio("GPU Data", PAGE_NAMES)
st.sidebar.caption("本地运行｜只读分析｜不保存客户源文件")

if page == "数据接入":
    render_data_intake()
elif page == "当前状况":
    render_current_status()
elif page == "调查线索":
    render_signals()
else:
    render_report()
