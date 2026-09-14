# Alibaba PAI T4 公开验证切片

本目录保存 8 个真实 Alibaba PAI T4 作业的确定性小切片，以及一次 Azure 官方公开零售价查询结果。它用于验证数据转换、质量门、成本与利用率计算，不代表任何企业的真实账单或 SLA。

## 来源与许可

- 原始数据：[Alibaba Cluster Trace Program / GPU v2020](https://github.com/alibaba/clusterdata/tree/master/cluster-trace-gpu-v2020)
- README 指定的下载镜像：[cluster-trace-gpu-v2020-data](https://github.com/qzweng/clusterdata-cluster-trace-gpu-v2020-data)
- 许可：[Creative Commons Attribution 4.0](https://creativecommons.org/licenses/by/4.0/)
- 价格来源：[Azure Retail Prices API](https://learn.microsoft.com/rest/api/cost-management/retail-prices/azure-retail-prices)

本仓库只提交可审查的小切片，并对字段做了转换。原始归档的 SHA-256、查询日期、接口条件和限制保存在 `source/source_metadata.json`。Alibaba 时间戳已确定性平移；团队、workload、region 和 SLA 语义属于派生或合成字段。

## 本地位置

- 原始大文件：`E:\DockerData\gpu-saas\validation\raw\alibaba-pai-2020`
- 转换结果：`E:\DockerData\gpu-saas\validation\prepared\alibaba-pai-t4-azure-eastus`
- 仓库内输入切片：`gpu-data\validation\alibaba_t4\source`

运行转换：

```powershell
python scripts\prepare-public-validation.py
```

运行已启动 Docker 产品的完整验证：

```powershell
python scripts\validate-public-stack.py
```
