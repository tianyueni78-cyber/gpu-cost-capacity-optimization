# GPU Cost & Capacity Copilot

面向中小型 AI 团队的 GPU 成本与容量决策产品。客户导入资源清单、使用记录、云账单和 SLA 后，系统完成字段映射、数据审计、成本归因、容量预测与优化测算，并输出带证据、收益和风险的行动建议。

> 当前阶段：本地客户版 MVP 已支持“上传 CSV → 引导式字段映射 → 自动数据审计”。成本归因、容量预测和优化建议将接在可信数据之后。

## 当前可用功能

- 分别上传 GPU 资源清单、使用记录、云账单和团队 SLA；
- 自动推荐中英文字段映射，由用户逐项确认；
- 检查主键重复、必填空值、数值范围、采购方式、日期格式和账单金额公式；
- 检查使用记录、账单与资源清单之间的资源池关联；
- 将发现分为“通过、警告、阻断”，并给出处理建议；
- 下载 UTF-8 编码的审计结果 CSV。

## 本地运行

```powershell
git clone https://github.com/tianyueni78-cyber/gpu-cost-capacity-optimization.git
cd gpu-cost-capacity-optimization
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
streamlit run app.py
```

浏览器会打开本地页面。四类文件的第一行必须是字段名；系统给出的映射只是建议，确认无误后再运行审计。

## 在线案例

- [GPU FinOps 管理驾驶舱](https://tianyueni78-cyber.github.io/ai-cloud-cost-optimization-/)
- [原始分析项目](https://github.com/tianyueni78-cyber/ai-cloud-cost-optimization-)

## 产品工作流

```text
导入数据
→ 确认字段映射
→ 数据审计
→ 成本与使用基线
→ 容量预测
→ 采购、共享与缩扩容优化
→ 收益和风险验证
→ 导出管理层报告
```

## 产品形态

- **公开演示版**：使用合成数据展示产品结果，兼作求职作品集。
- **本地客户版**：在客户或分析人员电脑上处理真实脱敏数据，不上传、不长期保存、不自动修改生产资源。
- **后续在线版**：真实需求得到验证后，再增加服务器、账号、历史项目和持续监控。

## 文档入口

- [产品设计](docs/产品设计.md)
- [学习与作品资产路线](docs/学习与作品资产路线.md)
- [GPU产品知识主线与学习顺序](docs/GPU产品知识主线与学习顺序.md)

## 第一版完成标准

1. 支持导入资源清单、使用记录、账单和 SLA；
2. 系统推荐字段映射，用户确认后继续；
3. 严重数据问题会阻断分析并提供修复建议；
4. 输出成本基线、容量预测和至少三类优化建议；
5. 每条建议包含证据、理论收益、风险和适用条件；
6. 支持导出管理层摘要与行动清单；
7. 客户数据不被公共演示环境保存；
8. 核心口径与安全规则具有自动测试。

当前已完成第 1—3 项的数据接入与审计闭环。下一产品里程碑是：只对审计通过的数据计算成本与容量基线。

## 项目原则

- 产品功能优先，求职展示由真实产品能力自然产生；
- 第一版使用普通 CPU，不需要 GPU 或付费 VPS；
- 不用学术版 Gurobi 部署收费服务；
- 不把理论节省表述为已实现收益；
- 不因低利用率直接建议回收高优先级或 SLA 保护资源。

## 数据与安全边界

- 当前版本在客户本机运行，不要求 GPU、VPS 或数据库；
- 上传内容只存在于当前 Streamlit 会话，不写入仓库或本地数据目录；
- 自动审计只读，不修改客户 CSV；
- 有阻断项时，不应继续生成成本或容量建议；
- 本项目不自动执行任何生产环境扩缩容或采购操作。

## 开发验证

```powershell
python -m unittest discover -s tests -v
python -m compileall app.py src tests
```

## License

[MIT License](LICENSE)
