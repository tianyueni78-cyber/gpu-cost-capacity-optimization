# GPU Data

GPU Data 帮助 AI 基础设施和平台团队发现 GPU 资源与成本问题。客户上传资源清单、使用记录、云账单和 SLA 后，产品检查数据可信度，展示成本与资源现状，生成可追溯的调查线索，并导出诊断报告。

> 当前形态是客户电脑上运行的本地 Web 应用，不是 SaaS。它不保存上传的源文件，不预测未来，不生成资源调整方案，也不执行生产操作。

## 产品结果

- 数据接入：字段映射、金额对账、关联检查和质量审计；
- 当前状况：净成本、成本归属、GPU 库存、活跃数量、利用率分布和 SLA 覆盖；
- 调查线索：观察、证据、相关成本、限制条件和负责人核查问题；
- 诊断报告：Markdown 管理摘要，以及指标、线索和数据质量 CSV。

“相关成本”表示某项线索涉及的成本规模，不等于可节省金额。低利用率也不直接代表资源可以回收。

## 本地运行

```powershell
git clone https://github.com/tianyueni78-cyber/gpu-cost-capacity-optimization.git
cd gpu-cost-capacity-optimization
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
streamlit run app.py
```

浏览器打开后按以下顺序使用：

```text
数据接入 → 当前状况 → 调查线索 → 诊断报告
```

必需输入是 GPU 资源清单、GPU 使用记录、GPU 云账单和团队 SLA。系统会推荐字段映射，但必须由用户确认。存在阻断项时，后三页不会生成分析结果。

## 产品家族

GPU Data 是四个可独立购买产品中的第一个：

- **GPU Data**：发现资源与成本问题；
- **GPU Optimize**：生成可审批的配置方案；
- **GPU Improve**：验证节省与运行效果；
- **GPU Forecast**：预测容量、成本与风险。

四个产品共用数据标准，但 GPU Data 不包含其他三个产品的能力。早期销售只针对客户当前最痛的问题，不主推四件套。

## 安全边界

- 文件只存在于当前 Streamlit 会话；
- 不写入数据库、仓库或公共演示环境；
- 审计和分析只读，不修改客户 CSV；
- 不调用云平台、Kubernetes 或调度系统；
- 不将受影响成本表述为已经实现的节省。

## 验证

```powershell
python -m unittest discover -s tests -v
python -m compileall app.py src tests
```

## 文档

- [产品设计](docs/产品设计.md)
- [30 分钟客户试点](docs/GPU-Data-试点验证.md)
- [学习与作品资产路线](docs/学习与作品资产路线.md)
- [GPU 产品知识主线与学习顺序](docs/GPU产品知识主线与学习顺序.md)

## License

[MIT License](LICENSE)
