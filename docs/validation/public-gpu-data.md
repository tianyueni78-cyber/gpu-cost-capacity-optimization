# GPU Data 公开数据专业验证

查询和验证日期：2026-09-14。

## 为什么这样验证

专业 FinOps 与 GPU 管理产品通常同时保留成本来源、资源遥测、数据质量、建议证据和人工决策边界。本阶段采用以下公开标准或产品能力作为设计参照：

| 参照 | 采用的产品原则 | 本阶段未采用 |
|---|---|---|
| [FinOps Framework](https://www.finops.org/framework/) 与 [FOCUS](https://focus.finops.org/) | 成本口径可追溯、分配维度明确、动态价格带查询上下文 | 完整 FOCUS 导入连接器 |
| [AWS Cost and Usage Reports](https://docs.aws.amazon.com/cur/latest/userguide/what-is-cur.html)、[Compute Optimizer](https://docs.aws.amazon.com/compute-optimizer/latest/ug/what-is-compute-optimizer.html) | 成本事实与建议分离，建议展示证据和风险 | AWS 正式连接器 |
| [Azure Cost Management](https://learn.microsoft.com/azure/cost-management-billing/costs/overview-cost-management)、[Azure Advisor](https://learn.microsoft.com/azure/advisor/advisor-overview) | 官方价格上下文、可审查建议 | 将公开零售价误作客户账单 |
| [Google Cloud Billing](https://cloud.google.com/billing/docs) 与 [Recommender](https://cloud.google.com/recommender/docs/overview) | 建议状态、来源和适用范围可追查 | GCP 正式连接器 |
| [NVIDIA DCGM](https://docs.nvidia.com/datacenter/dcgm/latest/user-guide/feature-overview.html) | GPU 利用率与显存遥测需要记录覆盖率和缺失状态 | 伪造无法从公开 trace 得到的显存百分比 |
| [Kubernetes Device Plugins](https://kubernetes.io/docs/concepts/extend-kubernetes/compute-storage-net/device-plugins/) 与 [OpenCost](https://www.opencost.io/docs/) | 分配量、使用量和成本是不同事实 | Kubernetes 自动变更 |
| Kubecost、CAST AI、Densify、CloudHealth | 从调查线索进入有证据、有限制、待人工审核的建议 | 自动执行或未经回测的节省承诺 |

这轮只实现最小闭环：不可变来源记录、转换、质量门、基线指标、调查信号、保守建议和报告。正式云连接器、机器学习和自动资源修改留到真实客户证据出现后。

## 数据源、下载位置与作用

| 步骤 | 网页或接口 | 先保存在哪里 | 目的/作用 |
|---|---|---|---|
| 1. 获取 GPU trace | [Alibaba GPU v2020](https://github.com/alibaba/clusterdata/tree/master/cluster-trace-gpu-v2020)；其 README 指向[数据镜像](https://github.com/qzweng/clusterdata-cluster-trace-gpu-v2020-data) | `E:\DockerData\gpu-saas\validation\raw\alibaba-pai-2020` | 提供真实作业、GPU 分配、等待时间和设备传感器记录 |
| 2. 校验归档 | README 给出的 SHA-256 | 同一 raw 目录 | 防止分片下载或拼接损坏 |
| 3. 获取公开价格 | [Azure Retail Prices API 文档](https://learn.microsoft.com/rest/api/cost-management/retail-prices/azure-retail-prices)；接口 `https://prices.azure.com/api/retail/prices` | 仓库切片中的 `azure_retail_price.json` | 为公开 trace 提供可复查的成本对照尺；不是 Alibaba 成本或客户协议价 |
| 4. 转成四表 | `python scripts\prepare-public-validation.py` | `E:\DockerData\gpu-saas\validation\prepared\alibaba-pai-t4-azure-eastus` | 生成 normal、blocked、missing-telemetry 三个确定性案例 |
| 5. 产品验证 | `python scripts\validate-public-stack.py` | PostgreSQL、E 盘产品数据卷和终端 JSON | 经真实 API/worker 跑 GPU Data，再持久化 GPU Optimize 建议 |

不需要把 1 GB 以上的原始传感器表提交到 Git。仓库内仅保留 8 个作业的小切片、来源元数据和官方价格响应，方便测试与审查。

## 字段映射与证据级别

| 产品字段 | 来源或计算 | 单位/粒度 | 缺失处理 | 证据级别 |
|---|---|---|---|---|
| `resource_pool_id` | `pai-job-` + `job_name` | 每作业 | 作业名缺失则转换失败 | 合理归纳 |
| `gpu_model` | task `gpu_type` | 每作业 | 缺失触发阻断 | 来源明确支持 |
| `gpu_count` | `sum(inst_num * plan_gpu / 100)` | GPU/作业 | 非数值触发审计 | 合理归纳 |
| `gpu_utilization_pct` | sensor `gpu_wrk_util` 的作业均值 | %/作业生命周期 | 保留空值并标记 `missing` | 来源明确支持 |
| `active_gpu_count` | `allocated_gpu_count * gpu_utilization_pct / 100` | GPU 等价值/作业 | 利用率缺失时为空 | 产品化推演 |
| `memory_utilization_pct` | 材料未提供可靠显存容量分母 | % | 始终为空，不用 GB 猜百分比 | 来源限制 |
| `queue_time_seconds` | `task_start - job_start`，下限 0 | 秒/作业 | 时间缺失则审计 | 合理归纳 |
| `billed_gpu_hours` | `gpu_count * duration_seconds / 3600` | GPU-hour/作业 | 输入缺失则阻断 | 产品化推演 |
| `unit_rate_usd` | Azure `Standard_NC4as_T4_v3` East US Linux Consumption | USD/hour | 动态查询，不写成永久常量 | 官方价格事实 |
| `net_cost_usd` | `billed_gpu_hours * 0.526` | USD/作业 | 无客户账单时只标为公开对照估算 | 产品化推演 |
| `team_id` | 匿名 user 派生 | 每作业 | 不解释为真实组织 | 合理归纳 |
| SLA 字段 | 合成 batch 案例 | 每派生 team | 只用于验证契约 | 产品化推演 |

价格记录的地区为 `eastus`，币种 USD，计费单位 `1 Hour`，API 记录生效日期 2021-11-01，查询日期 2026-09-14。价格会变化，使用时必须重新查询地区、操作系统、SKU 和采购类型。

## 独立基准与产品结果

对 8 个作业先用独立计算建立基准，再通过 Docker 中的 API、PostgreSQL、Redis 和 worker 运行产品：

| 指标 | 期望值 | 实测值 | 结论 |
|---|---:|---:|---|
| 作业数 | 8 | 8 | 通过 |
| 分配 GPU 数 | 20 | 20 | 通过 |
| GPU-hours | 2590.025833 | 2590.025833 | 通过 |
| 公开价格对照成本 | 1362.353588 USD | 1362.353588 USD | 通过 |
| GPU 利用率中位数 | 2.645860% | 2.645860% | 通过 |
| GPU 利用率 P95 | 84.972965% | 84.972965% | 通过 |
| 遥测覆盖率 | 100% | 100% | 通过 |
| Optimize 建议 | 有调查信号才生成 | 7 条 | 通过 |
| 理论节省 | 无商业证据不得宣称 | 全部 0 USD | 通过 |

正常案例发布成本、利用率、闲置调查线索与四类报告。删除必需的 `gpu_model` 后，质量门阻断正式分析。删除一条利用率遥测后，空值保留为 null 并触发阻断；系统没有把缺失值变成 0。两个阻断结果均不能生成 Optimize 建议。

## 建议边界

GPU Optimize 只把通过质量门的 `high_cost_low_activity` 与 `allocated_active_gap` 信号转为待人工审核建议。每条建议保存目标、行动、触发证据、观察窗口、阈值、覆盖率、相关成本、理论节省、SLA 风险、限制、人工步骤和来源 ID。同一数据集重复生成保持幂等。

公开 trace 缺少客户账单、折扣、业务 SLA、可回收性和变更结果，因此相关成本不能解释为可节省金额。真实节省必须在客户环境中经过 SLA 审核、批准、执行和前后对比。

## 故障排查

- 找不到 prepared 目录：先运行 `python scripts\prepare-public-validation.py`。
- Docker API 无法访问：运行 `.\scripts\local-stack.ps1 status`，再查看 `.\scripts\local-stack.ps1 logs`。
- 登录失败：检查本地 `.env` 中的 `LOCAL_DEV_EMAIL` 与 `LOCAL_DEV_PASSWORD`，不要把 `.env` 提交到 Git。
- 数值变化：先核对 `source_metadata.json`、归档 SHA-256 和 Azure 查询条件；动态价格变化时应建立新的带查询日期证据，不能覆盖旧结果。
