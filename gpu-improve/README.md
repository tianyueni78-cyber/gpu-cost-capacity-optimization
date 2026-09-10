# GPU Improve

GPU Improve 把 GPU 优化建议变成可追踪行动，并验证实际收益是否实现、是否损害 SLA。它不执行生产变更，也不把理论节省冒充已实现收益。

## 已完成功能

- 行动 CSV 校验与导入；
- 合法状态流转与只追加事件模型；
- 不可变基线、可比性准入和四级证据；
- 缩容、费率承诺、型号迁移、调度流程、避免采购五类验证方法；
- 行动重叠去重及 SLA、安全容量副作用检查；
- 已验证收益与成本规避分列；
- 四页 Streamlit 流程及中文台账、管理层报告导出；
- Supabase 六表结构、邮箱登录接口与 RLS 用户隔离。

## 本地演示

```powershell
cd gpu-improve
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
streamlit run app.py
```

未配置数据库时，页面显示“本地演示模式”，数据仅存在当前会话。可用 [行动导入示例](examples/actions.csv) 体验流程。

## Supabase 模式

1. 在 Supabase SQL Editor 执行 [schema.sql](supabase/schema.sql)。
2. 将 `.streamlit/secrets.example.toml` 复制为 `.streamlit/secrets.toml`。
3. 填入项目 URL 和 anon key，启用邮箱登录后启动应用。

不得填写 service-role key。原始账单和使用 CSV 不入库；数据库只保存项目、行动、事件、基线摘要、观察摘要和收益结果。

## 验证

```powershell
python -m unittest discover -s tests -v
python -m compileall app.py src tests
```

## 尚未实现

- 生产环境 Supabase 项目及正式域名部署；
- 企业 SSO、审批系统和工单系统集成；
- 自动采集云账单或监控数据；
- 自动执行任何生产资源变更。

产品规则见[正式规格](正式规格.md)，开发证据见[实施计划](实施计划.md)，试点方法见[试点验证](docs/GPU-Improve-试点验证.md)。
