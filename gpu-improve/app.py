"""GPU Improve：行动执行、收益验证与复盘。"""

from dataclasses import asdict, replace
from datetime import date, datetime, timezone
from io import BytesIO

import pandas as pd
import streamlit as st

from src.action_io import read_actions_csv
from src.benefits import verify_benefit
from src.comparability import check_comparability
from src.guards import SideEffectThresholds, evaluate_side_effects, finalize_result
from src.measurement import MetricSnapshot, freeze_baseline
from src.models import ActionRecord, ActionStatus, ActionType
from src.reporting import build_ledger, export_csv_bytes, render_executive_report
from src.workflow import can_verify, persist_then_export


PAGES = ("行动导入", "执行台账", "收益验证", "收益复盘")


def _database_configured():
    return bool(st.secrets.get("SUPABASE_URL") and st.secrets.get("SUPABASE_ANON_KEY"))


def _require_login():
    if not _database_configured():
        st.warning("本地演示模式：数据只保留在当前会话，刷新后会消失。")
        return
    if st.session_state.get("authenticated"):
        st.success("已登录，项目台账可持久保存。")
        return
    from supabase import create_client

    st.subheader("邮箱登录")
    email = st.text_input("邮箱")
    password = st.text_input("密码", type="password")
    if st.button("登录", type="primary"):
        try:
            client = create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_ANON_KEY"])
            response = client.auth.sign_in_with_password({"email": email, "password": password})
            st.session_state["authenticated"] = True
            st.session_state["supabase_client"] = client
            st.session_state["user_id"] = response.user.id
            st.rerun()
        except Exception:
            st.error("登录失败，请核对邮箱、密码和 Supabase 配置。")
    st.stop()


def _initial_state():
    st.session_state.setdefault("improve_actions", [])
    st.session_state.setdefault("benefit_results", [])


def _demo_snapshot(action_id: str, post: bool = False):
    return MetricSnapshot(
        action_id=action_id,
        resource_pool_ids=("GPU-001",),
        period_start=date(2026, 9, 1) if post else date(2026, 7, 1),
        period_end=date(2026, 10, 1) if post else date(2026, 7, 31),
        currency="USD",
        cost_basis="EFFECTIVE_COST",
        volume_unit="requests",
        variable_cost_usd=7000 if post else 8000,
        fixed_cost_usd=2000,
        business_volume=1000,
        availability_pct=99.95,
        p95_latency_ms=180,
        queue_time_seconds=4,
        failure_rate_pct=0.2,
        spare_capacity_pct=20,
        throughput_per_second=500,
        on_demand_equivalent_cost_usd=11000,
        planned_purchase_cost_usd=12000 if post else 20000,
    )


def render_import():
    st.title("行动导入")
    st.caption("从 GPU Optimize、标准 CSV 或人工录入建立待执行行动。")
    uploaded = st.file_uploader("上传行动 CSV", type=["csv"])
    if uploaded and st.button("校验并导入", type="primary"):
        parsed = read_actions_csv(BytesIO(uploaded.getvalue()))
        if parsed.errors:
            st.error("导入被阻断，请修复下列字段问题。")
            st.dataframe(pd.DataFrame(asdict(item) for item in parsed.errors), hide_index=True)
        else:
            existing = {item.action_id for item in st.session_state["improve_actions"]}
            st.session_state["improve_actions"].extend(
                item for item in parsed.records if item.action_id not in existing
            )
            st.success(f"已导入 {len(parsed.records)} 项行动。")
    st.download_button(
        "下载标准模板",
        open("examples/actions.csv", "rb").read(),
        "gpu_improve_actions.csv",
        "text/csv",
    )
    st.info("原始账单和使用 CSV 不上传数据库；只保存行动、汇总指标、证据和结果。")


def render_ledger():
    st.title("执行台账")
    actions = st.session_state["improve_actions"]
    if not actions:
        st.info("请先导入行动。")
        return
    frame = pd.DataFrame(asdict(item) for item in actions)
    st.dataframe(frame, use_container_width=True, hide_index=True)
    selected = st.selectbox("选择行动", [item.action_id for item in actions])
    status = st.selectbox("推进到", [item.value for item in ActionStatus])
    if st.button("记录状态变化"):
        st.session_state["improve_actions"] = [
            replace(item, status=ActionStatus(status)) if item.action_id == selected else item
            for item in actions
        ]
        st.success("状态已记录；数据库模式下应同时追加不可变事件。")


def render_verification():
    st.title("收益验证")
    actions = st.session_state["improve_actions"]
    if not actions:
        st.info("请先导入行动并完成执行。")
        return
    selected_id = st.selectbox("待验证行动", [item.action_id for item in actions])
    action = next(item for item in actions if item.action_id == selected_id)
    before = _demo_snapshot(selected_id)
    post = _demo_snapshot(selected_id, post=True)
    baseline = freeze_baseline(before, datetime.now(timezone.utc))
    comparability = check_comparability(baseline, post)
    if not can_verify(comparability):
        st.error("验证被阻断：" + "；".join(comparability.blocking_reasons))
        return
    st.success(f"可比性通过，证据等级：{comparability.evidence_grade}")
    if st.button("计算并保存收益", type="primary"):
        raw = verify_benefit(action, baseline, post, comparability)
        thresholds = SideEffectThresholds(99.9, 200, 5, 0.5, 10)
        result = finalize_result(raw, (), evaluate_side_effects(before, post, thresholds))
        st.session_state["benefit_results"] = [
            item for item in st.session_state["benefit_results"] if item.action_id != selected_id
        ] + [result]
        st.success(f"结论：{result.outcome}；已验证收益 ${result.realized_savings_usd:,.2f}")


def render_review():
    st.title("收益复盘")
    results = st.session_state["benefit_results"]
    if not results:
        st.info("完成至少一项收益验证后，本页才会生成正式台账。")
        return
    actions = {item.action_id: item for item in st.session_state["improve_actions"]}
    details = {
        key: {
            "project": "GPU成本优化",
            "owner": item.owner,
            "status": item.status.value,
            "estimated_savings_usd": item.estimated_savings_usd,
        }
        for key, item in actions.items()
    }
    ledger = build_ledger(results, details)
    st.metric("已验证收益", f"${ledger['已验证收益（USD）'].sum():,.2f}")
    st.metric("成本规避（单独列示）", f"${ledger['成本规避（USD）'].sum():,.2f}")
    st.dataframe(ledger, use_container_width=True, hide_index=True)
    st.download_button("下载收益台账", export_csv_bytes(ledger), "benefit_ledger.csv", "text/csv")
    st.download_button(
        "下载管理层报告", render_executive_report(ledger).encode("utf-8"),
        "executive_review.md", "text/markdown",
    )


st.set_page_config(page_title="GPU Improve", page_icon="📈", layout="wide")
_initial_state()
_require_login()
st.sidebar.title("GPU Improve")
page = st.sidebar.radio("工作流", PAGES)
{
    "行动导入": render_import,
    "执行台账": render_ledger,
    "收益验证": render_verification,
    "收益复盘": render_review,
}[page]()
