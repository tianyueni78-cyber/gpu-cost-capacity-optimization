# GPU Cost & Capacity Optimization

面向 AI 基础设施团队的 GPU 成本、容量和资源决策产品仓库。仓库按四个可独立使用、独立验证和独立部署的平台组织。

## 四个平台

| 平台 | 回答的问题 | 当前状态 | 入口 |
|---|---|---|---|
| GPU Data | 数据是否可信，钱花在哪里，资源如何使用？ | 已完成本地应用 | [进入目录](gpu-data/) |
| GPU Optimize | 在容量与 SLA 约束下，应调整哪些配置？ | 已完成容量优化阶段 | [进入目录](gpu-optimize/) |
| GPU Improve | 行动是否执行，实际收益是否实现？ | 已完成可运行 MVP | [进入目录](gpu-improve/) |
| GPU Forecast | 未来需要多少 GPU，何时采购或扩容？ | 已完成本地可运行 MVP | [进入目录](gpu-forecast/) |

每个平台的入口、代码、测试、依赖和说明都在自己的目录中。GPU Data 与 GPU Optimize 可以分别运行，不依赖另一个平台的代码目录。

## 统一本地环境

启动 Docker Desktop 后，在仓库根目录的普通 PowerShell 运行：

```powershell
.\scripts\local-stack.ps1 start
```

首次运行会自动生成本地 `.env`，Docker 持久数据固定保存在 `E:\DockerData\gpu-saas`。统一入口为 http://localhost:3000，登录邮箱和密码可在本地 `.env` 的 `LOCAL_DEV_EMAIL`、`LOCAL_DEV_PASSWORD` 中查看。

登录并选择组织与项目后进入 **GPU Data**。可以直接选择“使用样例数据”，也可以分别上传 `inventory.csv`、`usage.csv`、`billing.csv`、`sla.csv`。后台 worker 会调用既有 GPU Data 审计、基线和调查线索计算，结果与报告在重启后仍可读取。

样例成功标准：总成本 `1100 USD`、GPU 数量 `12`，并生成 Markdown 报告、闲置候选、数据质量和成本分摊四个下载文件。阻断级数据质量问题不会发布正式成本结论。

停止、查看状态和日志：

```powershell
.\scripts\local-stack.ps1 stop
.\scripts\local-stack.ps1 status
.\scripts\local-stack.ps1 logs
```

完整说明见 [Windows 本地生产等价环境](docs/operations/local-stack.md)。

## 文档

- [产品设计](产品设计.md)
- [四平台正式规格](四平台正式规格.md)
- [GPU Improve 正式规格](gpu-improve/正式规格.md)
- [GPU Forecast 正式规格](gpu-forecast/正式规格.md)

## 运行已完成的平台

以 GPU Data 为例：

```powershell
cd gpu-data
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
streamlit run app.py
```

GPU Optimize、GPU Improve 或 GPU Forecast 将第一行改为对应目录，其余命令相同。

## 验证

```powershell
cd gpu-data
python -m unittest discover -s tests -v

cd ..\gpu-optimize
python -m unittest discover -s tests -v

cd ..\gpu-improve
python -m unittest discover -s tests -v
```

## 在线分析案例

- [GPU FinOps 管理驾驶舱](https://tianyueni78-cyber.github.io/ai-cloud-cost-optimization-/)
- [完整分析案例仓库](https://github.com/tianyueni78-cyber/ai-cloud-cost-optimization-)

在线案例使用合成数据，不接收真实企业数据。

## 产品边界

- 当前为本地只读决策工具，不自动修改生产资源；
- 公开演示只使用合成数据；
- 理论节省、批准节省和实际收益严格区分；
- GPU Improve 已完成本地可运行 MVP；生产 Supabase 部署与外部系统集成仍未实现。
- GPU Forecast 已完成本地可运行 MVP；生产 Supabase 部署与企业系统集成仍未实施。

## License

[MIT License](LICENSE)
