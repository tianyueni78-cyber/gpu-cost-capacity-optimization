import streamlit as st


PAGES = ("数据与范围", "预测工作台", "容量情景", "计划与复盘")

st.set_page_config(page_title="GPU Forecast", page_icon="📈", layout="wide")
st.title("GPU Forecast")
st.caption("预测容量、成本与风险；不自动采购或修改生产资源。")

try:
    hosted = all(key in st.secrets for key in ("SUPABASE_URL", "SUPABASE_ANON_KEY"))
except Exception:
    hosted = False
if not hosted:
    st.info("本地演示模式：原始明细仅保留在当前会话，不会上传或长期保存。")

page = st.sidebar.radio("工作流", PAGES)

if page == "数据与范围":
    st.header("1. 数据与范围")
    st.write("上传业务历史、资源库存和容量规则，先判断预测准备度。")
    st.file_uploader("业务历史 CSV", type="csv")
    st.file_uploader("资源库存 CSV", type="csv")
    st.file_uploader("容量规则 CSV", type="csv")
    st.warning("存在阻断项时，不会生成正式预测或采购计划。")
elif page == "预测工作台":
    st.header("2. 预测工作台")
    st.write("比较三类可解释模型的滚动回测、区间与偏差，再确认业务事件和人工调整。")
    st.selectbox("决策模型", ("季节性朴素", "指数平滑", "趋势季节"))
    st.button("发布新预测版本", type="primary")
elif page == "容量情景":
    st.header("3. 容量情景")
    st.write("按团队、GPU 型号、区域分别查看 P50、P90、P99 容量和缺口。")
    st.segmented_control("容量口径", ("P50", "P90", "P99"), default="P90")
else:
    st.header("4. 计划与复盘")
    st.write("根据交付周期、价格有效期和证据等级形成待审批计划，并用实际值持续复盘。")
    st.download_button("导出采购行动 CSV", data=b"", file_name="gpu_forecast_actions.csv")
