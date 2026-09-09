"""GPU Optimize：本地容量约束、求解、比较与审批导出。"""

import pandas as pd
import streamlit as st

from src.audit import audit_tables
from src.capacity import build_capacity_input, peak_demands, solve_capacity, validate_capacity_input
from src.intake import DataInputError, apply_mapping, read_csv_bytes, suggest_mapping, validate_mapping
from src.optimize_reporting import build_approval_report, rows_csv
from src.recommendations import build_recommendations, set_recommendation_status
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

    st.write("按团队、GPU 型号和地域确认峰值需求。备用容量来自 SLA 表，系统不会自动放宽。")
    demands = {}
    for (team, model, region), default in peak_demands(tables["inventory"], tables["usage"]).items():
        demands[(team, model, region)] = st.number_input(
            f"{team}｜GPU 型号 {model}｜地域 {region}｜确认峰值需求",
            min_value=0, value=default, step=1,
            key=f"demand_{team}_{model}_{region}",
        )
    st.subheader("资源池共享边界")
    scope_labels = {"不可共享": "none", "团队内共享": "team", "跨团队共享": "cross_team"}
    sharing_scopes = {}
    for row in tables["inventory"].itertuples(index=False):
        label = st.selectbox(
            f"{row.resource_pool_id}｜{row.team_id}｜{row.gpu_model}｜{row.region}",
            list(scope_labels),
            key=f"sharing_{row.resource_pool_id}",
        )
        sharing_scopes[str(row.resource_pool_id).strip()] = scope_labels[label]
    hours = st.number_input("比较期间小时数", min_value=1, value=720, step=1)
    confirmed = st.checkbox("我已确认需求、SLA 备用容量与共享边界")
    if st.button("保存约束", type="primary", disabled=not confirmed):
        problem = build_capacity_input(tables, demands, sharing_scopes)
        errors = validate_capacity_input(problem)
        if errors:
            for error in errors:
                st.error(error)
        else:
            st.session_state["capacity_problem"] = problem
            st.session_state["comparison_hours"] = int(hours)
            st.session_state["constraints_confirmed"] = True
            demand_rows = [
                {"team_id": key[0], "gpu_model": key[1], "region": key[2], "confirmed_peak": int(value)}
                for key, value in demands.items()
            ]
            sharing_rows = [
                {"resource_pool_id": pool_id, "sharing_scope": scope}
                for pool_id, scope in sharing_scopes.items()
            ]
            st.session_state["constraint_snapshot"] = demand_rows + sharing_rows
            st.session_state["confirmed_constraints"] = [
                f"{key[0]} / {key[1]} / {key[2]} 峰值需求 {int(value)} 张 GPU"
                for key, value in demands.items()
            ]
            st.success("约束已确认，可以运行容量求解。")


def render_capacity() -> None:
    st.title("容量优化")
    tables = require_clean_baseline()
    problem = st.session_state.get("capacity_problem")
    if tables is None or problem is None:
        return
    solution = solve_capacity(problem)
    scenario_result = build_capacity_scenarios(
        problem, solution, period_hours=st.session_state["comparison_hours"]
    )
    timestamps = pd.to_datetime(tables["usage"]["timestamp_utc"], errors="coerce", utc=True)
    period = "未提供"
    if timestamps.notna().any():
        period = f"{timestamps.min().date()} 至 {timestamps.max().date()}"
    recommendations = build_recommendations(problem, solution, scenario_result, period)
    st.session_state["capacity_solution"] = solution
    st.session_state["scenario_result"] = scenario_result
    st.session_state["recommendations"] = recommendations
    if solution.status == "infeasible":
        st.error("；".join(solution.conflicts))
    else:
        st.success("已找到满足确认约束的容量方案。")
    st.subheader("方案比较")
    st.dataframe(pd.DataFrame(scenario_result["scenarios"]), use_container_width=True, hide_index=True)
    st.subheader("兼容范围与建议证据")
    for item in recommendations:
        with st.expander(f"{item['recommendation_id']}｜{item['status']}", expanded=True):
            st.write(f"**受影响资源：** {item['affected_resources']}")
            st.write(f"**观察期间：** {item['period']}")
            st.write(f"**当前配置：** {item['current_configuration']}")
            st.write(f"**建议配置：** {item['proposed_configuration']}")
            st.write(f"**SLA 风险：** {item['sla_risk']}")
            st.write(f"**限制：** {item['limitation']}")
    st.subheader("资源池调整明细")
    st.dataframe(pd.DataFrame(scenario_result["pool_adjustments"]), use_container_width=True, hide_index=True)
    st.caption("受影响成本不是已验证节省；采购合同与实际费率需在采购优化阶段复核。")


def render_approval() -> None:
    st.title("方案与审批")
    if require_clean_baseline() is None:
        return
    scenario_result = st.session_state.get("scenario_result")
    recommendations = st.session_state.get("recommendations")
    if not scenario_result or recommendations is None:
        st.info("请先运行容量优化。")
        return
    st.subheader("建议审批状态")
    statuses = ("待确认", "待审批", "推迟", "不适用")
    for item in list(recommendations):
        selected = st.selectbox(
            item["recommendation_id"], statuses,
            index=statuses.index(item["status"]),
            key=f"status_{item['recommendation_id']}",
        )
        if selected != item["status"]:
            recommendations = set_recommendation_status(
                recommendations, item["recommendation_id"], selected
            )
    st.session_state["recommendations"] = recommendations
    report = build_approval_report(
        {"period": f"{st.session_state['comparison_hours']} 小时"},
        scenario_result["scenarios"],
        st.session_state.get("confirmed_constraints", []),
        recommendations,
        scenario_result["pool_adjustments"],
    )
    st.markdown(report)
    st.download_button("下载审批报告", report.encode("utf-8"), "gpu_optimize_capacity.md")
    st.download_button("下载建议 CSV", rows_csv(recommendations), "gpu_optimize_recommendations.csv", "text/csv")
    st.download_button("下载资源池调整 CSV", rows_csv(scenario_result["pool_adjustments"]), "gpu_optimize_pool_adjustments.csv", "text/csv")
    st.download_button("下载约束快照 CSV", rows_csv(st.session_state.get("constraint_snapshot", [])), "gpu_optimize_constraints.csv", "text/csv")


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
