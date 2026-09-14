# Windows 本地生产等价环境

## 启动

前提：Windows 已安装 Docker Desktop，且 Docker 数据盘仍配置在 `E:\DockerData`。在仓库根目录的普通 PowerShell 中运行一条命令：

```powershell
.\scripts\local-stack.ps1 start
```

首次启动会在被 Git 忽略的 `.env` 中生成本地密码和随机密钥，并在 `E:\DockerData\gpu-saas` 创建 PostgreSQL、Redis 数据目录。登录邮箱为 `student@example.com`，密码读取方式：

```powershell
Get-Content .env | Select-String LOCAL_DEV_PASSWORD
```

- 统一入口：http://localhost:3000
- API 健康：http://localhost:8000/healthz
- API 文档：http://localhost:8000/docs

## 验证 GPU Data

1. 登录后选择组织和项目，进入 **GPU Data**。
2. 点击“使用样例数据”，确认四张表均显示文件名和行数。
3. 点击“开始真实分析”。后台完成后应显示总成本 `1100 USD`、GPU 数量 `12`、成本归因覆盖率、利用率分布和闲置候选。
4. 下载 `report.md`、`idle_candidates.csv`、`data_quality.csv`、`cost_allocation.csv`。
5. 上传自己的四张 CSV 时，阻断级质量问题只显示审计结果，不发布正式成本结论；警告级问题保留结果并注明限制。

数据集、分析结果和下载记录按组织与项目隔离。原始 CSV 与报告保存在 `E:\DockerData\gpu-saas`，不要在其中放入访问密钥或未脱敏的个人信息。

## 停止与检查

```powershell
.\scripts\local-stack.ps1 status
.\scripts\local-stack.ps1 logs
.\scripts\local-stack.ps1 stop
```

`stop` 不删除 E 盘数据。再次 `start` 后，组织、项目和任务记录继续存在。

## 故障排查

1. **Docker named pipe 不存在**：运行 `docker info`。若提示 `dockerDesktopLinuxEngine` named pipe 不存在，先启动 Docker Desktop；若后端崩溃，查看 `%LOCALAPPDATA%\Docker\log\host\com.docker.backend.exe.log`。
   若日志明确出现 `sailor-ingest.sock ... file cannot be accessed by the system`，先重启 Windows，再打开 Docker Desktop。不要选择恢复出厂设置，否则会增加本地数据丢失风险。
2. **Windows 权限**：普通 PowerShell 应可运行。只有 Docker Desktop 本身提示权限时才检查当前用户是否能访问 Docker 引擎。
3. **端口占用**：运行 `Get-NetTCPConnection -LocalPort 3000,8000`，停止占用端口的旧开发服务后重试。
4. **安全软件拦截**：若镜像下载或 bind mount 被拦截，在安全软件事件中确认具体文件和进程，仅对 Docker Desktop 组件放行。
5. **服务不健康**：运行日志命令，按 postgres、redis、api、worker、web 的首个错误定位，不删除 `E:\DockerData\gpu-saas`。

## 已验证

- 本地开发登录、组织和项目选择。
- 四产品受控入口。
- PostgreSQL、Redis、API、worker、Next.js 健康检查。
- 任务携带租户与幂等键，worker 更新任务状态。
- 容器重启后组织、项目和任务仍存在。
- PostgreSQL RLS 拒绝跨租户读写。
- GPU Data 的代码级样例分析、阻断门禁、API、迁移和权限测试。
- GPU Data 样例与坏数据实机分析、报告下载、幂等、容器重启持久化和跨租户 RLS。
- PostgreSQL/Redis 同时重启后 worker 自动恢复。

## 尚未完成

- AWS、Kubernetes、Prometheus 正式连接器。
- 支付宝、企业 SSO、ICP备案和生产部署。
- 自动修改 GPU 或客户基础设施。
- GPU Optimize、GPU Improve、GPU Forecast 的计算界面仍通过受控独立页面接入；GPU Data 已接入统一页面且复用原计算核心。
