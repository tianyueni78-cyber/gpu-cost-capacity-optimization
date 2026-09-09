# GPU Optimize

GPU Optimize 把经过审计的 GPU 资源、使用、账单和 SLA 数据，转换成满足客户确认约束的可审批配置方案。

> 当前分支只上线“容量分配优化”。采购组合和运行配置仍在后续阶段，页面中不会展示尚未验证的空壳功能。

## 当前可用结果

- 上传四张 CSV，完成字段映射与数据审计；
- 按团队、GPU 型号和地域确认峰值需求与 SLA 备用容量；
- 逐资源池确认不可共享、团队内共享或跨团队共享；
- 使用整数求解器在同型号、同地域范围内计算安全容量；
- 比较当前、安全释放和低变更方案；
- 无可行方案时说明 GPU 缺口，不自动放松约束；
- 使用实际资源池费率计算受影响成本，不使用平均费率；
- 展示受影响资源、观察期间、风险、限制和审批状态；
- 导出审批报告、建议、资源池调整和约束快照 CSV。

受影响成本表示可调整容量对应的成本规模，不是已验证节省。共享容量不会自动降低账单；采购合同、退出费用和实际折扣要在采购优化阶段复核。

## 本地运行

```powershell
git clone https://github.com/tianyueni78-cyber/gpu-cost-capacity-optimization.git
cd gpu-cost-capacity-optimization
cd gpu-optimize
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
streamlit run app.py
```

页面顺序：

```text
基线接入 → 目标与约束 → 容量优化 → 方案与审批
```

## 产品边界

- GPU Data 负责数据清洗、成本对账和问题发现；
- GPU Forecast 或用户提供未来需求与峰值；
- GPU Optimize 负责约束建模、方案求解、风险解释和审批材料；
- GPU Improve 负责实施后的节省与运行效果验证；
- 客户负责人决定是否执行方案。

本产品不自动修改云资源、Kubernetes 或生产集群。

H100 不会自动替代 A100，不同地域也不会自动共享。缺少已确认需求或共享权限时，资源池保持现状并标记为待确认。

## 专业依据

- [FinOps Usage Optimization](https://www.finops.org/framework/capabilities/usage-optimization/)
- [FinOps Rate Optimization](https://www.finops.org/framework/capabilities/rate-optimization/)
- [AWS Compute Optimizer](https://docs.aws.amazon.com/compute-optimizer/latest/ug/view-ec2-recommendations.html)
- [Azure Savings Plan recommendations](https://learn.microsoft.com/en-us/azure/cost-management-billing/savings-plan/purchase-recommendations)
- [NVIDIA GPU Sharing](https://docs.nvidia.com/datacenter/cloud-native/gpu-operator/latest/gpu-sharing.html)

## 验证

```powershell
python -m unittest discover -s tests -v
python -m compileall app.py src tests
```

## 文档

- [总产品设计](../产品设计.md)
- [四平台正式规格](../四平台正式规格.md)
- [30 分钟客户试点](docs/GPU-Optimize-容量试点.md)

## License

[MIT License](../LICENSE)
