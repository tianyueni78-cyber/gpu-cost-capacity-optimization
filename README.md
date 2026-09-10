# GPU Cost & Capacity Optimization

面向 AI 基础设施团队的 GPU 成本、容量和资源决策产品仓库。仓库按四个可独立使用、独立验证和独立部署的平台组织。

## 四个平台

| 平台 | 回答的问题 | 当前状态 | 入口 |
|---|---|---|---|
| GPU Data | 数据是否可信，钱花在哪里，资源如何使用？ | 已完成本地应用 | [进入目录](gpu-data/) |
| GPU Optimize | 在容量与 SLA 约束下，应调整哪些配置？ | 已完成容量优化阶段 | [进入目录](gpu-optimize/) |
| GPU Improve | 行动是否执行，实际收益是否实现？ | 已完成可运行 MVP | [进入目录](gpu-improve/) |
| GPU Forecast | 未来需要多少 GPU，何时采购或扩容？ | 待开发 | [查看边界](gpu-forecast/) |

每个平台的入口、代码、测试、依赖和说明都在自己的目录中。GPU Data 与 GPU Optimize 可以分别运行，不依赖另一个平台的代码目录。

## 文档

- [产品设计](产品设计.md)
- [四平台正式规格](四平台正式规格.md)
- [GPU Improve 正式规格](gpu-improve/正式规格.md)

## 运行已完成的平台

以 GPU Data 为例：

```powershell
cd gpu-data
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
streamlit run app.py
```

GPU Optimize 或 GPU Improve 将第一行改为对应目录，其余命令相同。

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
- GPU Forecast 尚未完成，README 不把规划功能描述成已上线能力。

## License

[MIT License](LICENSE)
