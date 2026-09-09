"""GPU Optimize：本地容量约束、求解、比较与审批导出。"""

import pandas as pd
import streamlit as st

from src.audit import audit_tables
from src.capacity import build_capacity_input, peak_demands, solve_capacity, validate_capacity_input
from src.intake import DataInputError, apply_mapping, read_csv_bytes, suggest_mapping, validate_mapping
from src.optimize_reporting import build_approval_report, scenarios_csv
from src.scenarios import build_capacity_scenarios
from src.schema import TABLE_SPECS
from src.workflow import ready_for_audit, ready_for_optimization


PAGES = ("基线接入", "目标与约束", "容量优化", "方案与审批")


def require_clean_baseline() -> dict | None:
    tables = st.session_state.get("mapped_tables")
    audit = st.session_state.get("audit_result")
    if not ready_for_optimization(audit, st.session_state.get("constraints_confirmed", False)):
        st.info("请先完成基线审计并确认约束。")
        return None
    return tables


def render_intake() -> None:
    st.title("基线接入")
    st.caption("上传四张标准业务表，确认字段映射并通过数据审计。")
    uploaded_frames = {}
    columns = st.columns(2)
    for index, (role, spec) in enumerate(TABLE_SPECS.items()):
        with columns[index % 2]:
            uploaded = st.file_uploader(spec.label_zh, type=["csv"], key=f"upload_{role}")
            if uploaded is not None:
                try:
                    frame = read_csv_bytes(uploaded.getvalue())
                    uploaded_frames[role] = frame
                    st.success(f"已读取 {len(frame):,} 行 × {len(frame.columns)} 列")
                except DataInputError as exc:
                    st.error(str(exc))

    mapped_tables = {}
    mapping_errors = {}
    for role, frame in uploaded_frames.items():
        spec = TABLE_SPECS[role]
        suggestions = suggest_mapping(frame.columns, spec)
        with st.expander(f"{spec.label_zh}字段映射", expanded=True):
            options = ["— 不映射 —"] + list(frame.columns)
            mapping = {}
            for field in spec.required_fields + spec.optional_fields:
                selected = st.selectbox(
                    spec.field_labels[field] + (" *" if field in spec.required_fields else ""),
                    options,
                    index=options.index(suggestions[field]) if suggestions[field] in options else 0,
                    key=f"mapping_{role}_{field}",
                )
                mapping[field] = None if selected == "— 不映射 —" else selected
            mapping_errors[role] = validate_mapping(mapping, spec)
            for error in mapping_errors[role]:
                st.error(error)
            if not mapping_errors[role]:
                mapped_tables[role] = apply_mapping(frame, mapping)

    if st.button("运行自动审计", type="primary", disabled=not ready_for_audit(mapped_tables, mapping_errors)):
        st.session_state["mapped_tables"] = mapped_tables
        st.session_state["audit_result"] = audit_tables(mapped_tables)
        st.session_state["constraints_confirmed"] = False

    audit = st.session_state.get("audit_result")
    if audit is not None:
        blocking = audit["status"].eq("异常") & audit["severity"].eq("阻断")
        if blocking.any():
            st.error("存在阻断项，不能进入容量优化。")
        else:
            st.success("基线审计通过，可以确认业务约束。")
        st.dataframe(audit, use_container_width=True, hide_index=True)


def render_constraints() -> None:
    st.title("目标与约束")
    tables = st.session_state.get("mapped_tables")
    audit = st.session_state.get("audit_result")
    if audit is None or tables is None or not ready_for_optimization(audit, True):
        st.info("请先上传数据并通过基线审计。")
        return

    st.write("确认各团队本期峰值需求。备用容量来自 SLA 表，系统不会自动放宽。")
    demands = {}
    for team, default in peak_demands(tables["inventory"], tables["usage"]).items():
        demands[team] = st.number_input(
            f"{team} 确认峰值需求（GPU 数）", min_value=0, value=default, step=1
        )
    hours = st.number_input("比较期间小时数", min_value=1, value=720, step=1)
    confirmed = st.checkbox("我已确认需求、SLA 备用容量与共享边界")
    if st.button("保存约束", type="primary", disabled=not confirmed):
        problem = build_capacity_input(tables, demands)
        errors = validate_capacity_input(problem)
        if errors:
            for error in errors:
                st.error(error)
        else:
            st.session_state["capacity_problem"] = problem
            st.session_state["comparison_hours"] = int(hours)
            st.session_state["constraints_confirmed"] = True
            st.session_state["confirmed_constraints"] = [
                f"{team} 峰值需求 {int(demand)} 张 GPU" for team, demand in demands.items()
            ]
            st.success("约束已确认，可以运行容量求解。")


def render_capacity() -> None:
    st.title("容量优化")
    tables = require_clean_baseline()
    problem = st.session_state.get("capacity_problem")
    if tables is None or problem is None:
        return
    rates = pd.to_numeric(tables["inventory"]["effective_hourly_rate_usd"], errors="coerce")
    hourly_rate = float(rates.mean()) if not rates.empty else 0.0
    scenarios = build_capacity_scenarios(
        problem, hourly_rate=hourly_rate, hours=st.session_state["comparison_hours"]
    )
    st.session_state["capacity_scenarios"] = scenarios
    solution = solve_capacity(problem)
    if solution.status == "infeasible":
        st.error("；".join(solution.conflicts))
    else:
        st.success("已找到满足确认约束的容量方案。")
    st.dataframe(pd.DataFrame(scenarios), use_container_width=True, hide_index=True)
    st.caption("受影响成本不是已验证节省；采购合同与实际费率需在采购优化阶段复核。")


def render_approval() -> None:
    st.title("方案与审批")
    if require_clean_baseline() is None:
        return
    scenarios = st.session_state.get("capacity_scenarios")
    if not scenarios:
        st.info("请先运行容量优化。")
        return
    report = build_approval_report(
        {"period": f"{st.session_state['comparison_hours']} 小时"},
        scenarios,
        st.session_state.get("confirmed_constraints", []),
    )
    st.markdown(report)
    st.download_button("下载审批报告", report.encode("utf-8"), "gpu_optimize_capacity.md")
    st.download_button("下载方案 CSV", scenarios_csv(scenarios), "gpu_optimize_scenarios.csv", "text/csv")


st.set_page_config(page_title="GPU Optimize", page_icon="⚙️", layout="wide")
st.sidebar.title("GPU Optimize")
st.sidebar.caption("当前已上线：容量分配优化")
st.sidebar.warning("方案仅供审批，不会修改生产资源。")
page = st.sidebar.radio("工作流", PAGES)

if page == "基线接入":
    render_intake()
elif page == "目标与约束":
    render_constraints()
elif page == "容量优化":
    render_capacity()
else:
    render_approval()
