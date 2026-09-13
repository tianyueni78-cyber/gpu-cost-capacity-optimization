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

## 停止与检查

```powershell
.\scripts\local-stack.ps1 status
.\scripts\local-stack.ps1 logs
.\scripts\local-stack.ps1 stop
```

`stop` 不删除 E 盘数据。再次 `start` 后，组织、项目和任务记录继续存在。

## 故障排查

1. **Docker named pipe 不存在**：运行 `docker info`。若提示 `dockerDesktopLinuxEngine` named pipe 不存在，先启动 Docker Desktop；若后端崩溃，查看 `%LOCALAPPDATA%\Docker\log\host\com.docker.backend.exe.log`。
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

## 尚未完成

- AWS、Kubernetes、Prometheus 正式连接器。
- 支付宝、企业 SSO、ICP备案和生产部署。
- 自动修改 GPU 或客户基础设施。
- 四个 Streamlit 计算界面的统一重写；当前通过受控独立页面接入，计算核心保持原样。
