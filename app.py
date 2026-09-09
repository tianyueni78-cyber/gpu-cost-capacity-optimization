"""GPU 成本与容量优化平台：CSV 接入、字段映射与数据审计。"""

import streamlit as st

from src.audit import audit_tables
from src.intake import DataInputError, apply_mapping, read_csv_bytes, suggest_mapping, validate_mapping
from src.schema import TABLE_SPECS
from src.workflow import ready_for_audit


st.set_page_config(page_title="GPU Cost & Capacity Copilot", page_icon="⚙️", layout="wide")

st.title("GPU Cost & Capacity Copilot")
st.caption("先证明数据可信，再讨论成本、容量与采购优化。")
st.info("隐私边界：上传文件仅保留在当前本地会话，不写入磁盘；本阶段只生成审计结论，不修改源数据或生产资源。")

st.header("1. 上传四类业务 CSV")
st.write("每个入口对应一种业务角色，避免系统把账单误认成使用记录。")

uploaded_frames = {}
upload_columns = st.columns(2)
for index, (role, spec) in enumerate(TABLE_SPECS.items()):
    with upload_columns[index % 2]:
        uploaded = st.file_uploader(
            spec.label_zh,
            type=["csv"],
            key=f"upload_{role}",
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
st.write("系统只提供建议。你确认每个客户字段对应哪个标准字段；“*”表示必填。")

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
                    f"{label}  →  `{field}`",
                    options,
                    index=default_index,
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
    st.session_state["audit_result"] = audit_tables(mapped_tables)

if "audit_result" in st.session_state and is_ready:
    result = st.session_state["audit_result"]
    abnormal = result[result["status"] == "异常"]
    metrics = st.columns(3)
    metrics[0].metric("通过", int((result["status"] == "通过").sum()))
    metrics[1].metric("警告", int(((result["status"] == "异常") & (result["severity"] == "警告")).sum()))
    metrics[2].metric("阻断", int(((result["status"] == "异常") & (result["severity"] == "阻断")).sum()))

    if (abnormal["severity"] == "阻断").any():
        st.error("存在阻断项：在修复或确认规则前，不应进入成本与容量优化。")
    elif not abnormal.empty:
        st.warning("没有阻断项，但警告项需要在报告中说明。")
    else:
        st.success("当前规则范围内全部通过，可以进入下一阶段分析。")

    display = result.copy()
    display["table_name"] = display["table_name"].map({role: spec.label_zh for role, spec in TABLE_SPECS.items()})
    st.dataframe(display, use_container_width=True, hide_index=True)
    st.download_button(
        "下载审计报告 CSV",
        data=result.to_csv(index=False).encode("utf-8-sig"),
        file_name="gpu_data_audit_report.csv",
        mime="text/csv",
    )
