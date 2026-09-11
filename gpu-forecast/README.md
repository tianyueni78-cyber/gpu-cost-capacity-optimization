# GPU Forecast

GPU Forecast 用于预测未来业务量、GPU 容量与成本，支持预算、采购和扩容时点决策。

## 当前状态

本地可运行 MVP 已完成：数据准备度、无泄漏滚动回测、三类可解释模型、不可变预测版本、P50/P90/P99 容量情景、采购计划、四页 Web 工作流及 CSV/管理摘要导出。

工作流：

```text
范围与业务驱动 → 时间回测 → 需求与容量情景 → 采购预算计划
```

商业定位、页面工作流、数据模型、公式、安全边界和验收标准见[GPU Forecast 正式规格](正式规格.md)，平台间边界见[四平台正式规格](../四平台正式规格.md)。

## 本地运行

```powershell
pip install -r requirements.txt
streamlit run app.py
```

没有 Supabase Secrets 时自动进入本地演示模式。产品只生成决策建议，不自动采购或调整生产资源。客户试点见 [30 分钟试点脚本](docs/GPU-Forecast-试点验证.md)。
