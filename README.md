# GPU Cost & Capacity Copilot

面向 AI 基础设施团队的 GPU 成本与容量决策平台。

平台采用“一个共享底座＋四个可独立购买模块”的产品结构：客户可以只解决当前最紧迫的问题，也可以逐步形成从可信数据、优化决策到收益验证的完整闭环。

> 产品原则：先证明数据可信，再提出不会破坏 SLA 的优化建议；理论节省不等于已实现收益。

## 在线案例

- [GPU FinOps 管理驾驶舱](https://tianyueni78-cyber.github.io/ai-cloud-cost-optimization-/)
- [完整分析案例](https://github.com/tianyueni78-cyber/ai-cloud-cost-optimization-)

在线案例使用合成数据，不接收真实企业数据。

## 产品结构

| 模块 | 客户问题 | 核心交付 |
|---|---|---|
| **GPU Data** | 钱花在哪、资源如何使用、数据是否可信？ | 数据审计、成本与使用基线、调查线索 |
| **GPU Optimize** | 哪些配置值得调整，哪个方案更安全？ | 优化机会卡、方案模拟、决策包 |
| **GPU Improve** | 行动是否执行，实际节省是否实现？ | 行动台账、前后对比、收益验证 |
| **GPU Forecast** | 未来需要多少 GPU，何时采购？ | 需求预测、容量情景、采购时间建议 |

四个模块共享字段映射、数据版本、指标口径、SLA约束和审计证据，但可以独立使用和交付。

## 完整决策闭环

```text
创建分析项目
→ 上传数据与字段映射
→ 数据审计门禁
→ 当前状态与成本归属          GPU Data
→ 生成优化机会
→ 方案模拟与人工审批          GPU Optimize
→ 记录并执行行动
→ 验证实际收益                GPU Improve
→ 预测未来需求与容量          GPU Forecast（可选）
→ 返回下一轮分析
```

## 当前已经完成

当前 `main` 版本支持：

```text
上传四类 CSV
→ 推荐并确认字段映射
→ 自动数据审计
→ 区分通过、警告与阻断
→ 下载审计报告
```

支持检查主键与业务键重复、必填空值、数值范围、采购方式、时间格式、账单金额公式、合同条件和资源池跨表关联。

## 产品边界

- 当前版本在客户本机运行，不要求 GPU、VPS或数据库；
- 上传内容只存在于当前会话，不写入仓库；
- 有阻断项时，不生成依赖该数据的结论；
- 第一版只提供建议和行动清单，不修改生产资源；
- 不把受影响成本或潜在节省表述为实际收益；
- 暂不开发实时GPU调度、多租户计费和Kubernetes自动接入。

## 开发路线

1. 完成 GPU Data：可信数据、成本归属、资源现状和调查线索；
2. 开发 GPU Optimize：机会卡、冲突去重、方案模拟和决策包；
3. 开发 GPU Improve：行动状态与实际收益验证；
4. 开发 GPU Forecast：回测可靠后再接入容量决策；
5. 获得真实客户需求后，再考虑云接口和审批式自动执行。

## 本地运行

```powershell
git clone https://github.com/tianyueni78-cyber/gpu-cost-capacity-optimization.git
cd gpu-cost-capacity-optimization
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
streamlit run app.py
```

## 开发验证

```powershell
python -m unittest discover -s tests -v
python -m compileall app.py src tests
```

## 文档

- [产品设计](docs/产品设计.md)
- [B2决策工作台正式规格](docs/superpowers/specs/2026-09-10-gpu-decision-workbench-design.md)
- [学习与作品资产路线](docs/学习与作品资产路线.md)
- [GPU产品知识主线与学习顺序](docs/GPU产品知识主线与学习顺序.md)

## 专业依据

产品工作流参考 [FinOps Foundation](https://www.finops.org/framework/phases/) 的 Inform、Optimize、Operate 循环，并吸收 [AWS Cost Optimization](https://docs.aws.amazon.com/wellarchitected/latest/framework/a-cost-optimization.html)、[Google Cloud FinOps Hub](https://docs.cloud.google.com/billing/docs/how-to/finops-hub?hl=en)、[Vantage Cost Recommendations](https://docs.vantage.sh/cost_recommendations) 和 [NVIDIA Run:ai](https://run-ai-docs.nvidia.com/saas/platform-management/runai-scheduler/scheduling/how-the-scheduler-works) 的实践。

## License

[MIT License](LICENSE)
