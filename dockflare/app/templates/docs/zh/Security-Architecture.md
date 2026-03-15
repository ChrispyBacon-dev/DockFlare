# DockFlare 安全架构与加固

本文说明 DockFlare 3.0+ 如何保护主控端和已注册的代理端，并补充内建防护机制与推荐运维实践。

## 1. 控制平面信任模型

- **主控端是唯一可信源** - DockFlare 主控端保存所有 Cloudflare 凭据和策略定义。代理端不会直接管理 API 令牌，而是通过经过身份验证的通道接收并执行指令。
- **每个代理端使用独立 API 密钥** - 注册流程需要由主控端签发唯一 API 密钥。密钥与所有者、时间戳、状态等元数据一起保存在加密的 `agent_keys.dat` 中，因此可以随时轮换或吊销。
- **主控端 API 受保护** - 管理端点（网页管理界面、`/api/v2/*`）需要有效会话或 Master API 密钥。令牌会在响应和日志中被遮蔽，并且可以在不重启整个栈的情况下完成轮换。

## 2. 加密配置与密钥管理

- **加密的 `dockflare_config.dat`** - Cloudflare 凭据、界面账户、隧道默认设置和主密钥都保存在由 `dockflare.key` 保护的加密 blob 中。
- **加密的代理注册表** - Agent API 密钥及其审计元数据保存在 `agent_keys.dat` 中，并使用同一个 Fernet 密钥加密。敏感信息不再出现在 `state.json` 中。
- **恢复后自动重启** - 恢复备份归档时，DockFlare 会写入加密文件、重新加载运行时状态、设置重启标志并退出。随后 Docker 的重启策略会立即使用新配置拉起容器。
- **`state.json` 保持明文以便观测** - `state.json` 仍然是明文文件，便于运维人员检查规则和代理端状态。所有密钥和敏感配置仍以加密文件为准。

## 3. 备份与恢复保障

- **归档内容完整** - 每个备份归档 (`dockflare_backup_*.zip`) 都包含 `dockflare_config.dat`、`dockflare.key`、`agent_keys.dat`、`state.json` 和包含校验和及版本元数据的 `manifest.json`。重建主控端节点不需要额外文件。
- **恢复流程自动化** - 通过初始向导或设置页面执行恢复时，DockFlare 会写入归档文件、重新加载运行时缓存并强制重启容器，使加密配置立即生效。
- **兼容旧版恢复方式** - 仍支持单独上传 `state.json` 用于故障排查或部分迁移。DockFlare 会导入运行时状态，但保留现有的加密配置，避免误清空凭据。

## 4. 网络与通信安全

- **通过 Cloudflare Tunnel 传输** - 代理端不暴露入站端口。所有流量都通过主控端管理的 Cloudflare Tunnel 传输，从而减少远程主机上的攻击面。
- **经过认证的代理调用** - 代理端的 REST 调用会附带自己的 API 密钥，并与已登记的 Agent ID 绑定。令牌不匹配或已吊销的密钥会被拒绝。
- **Redis 背板** - DockFlare 依赖 Redis 提供缓存、日志流和跨线程信号。推荐的 Compose 栈会将 Redis 放在独立的 `dockflare-internal` 网络上，避免 `cloudflare-net` 上的工作负载直接访问它。若使用外部 Redis，请启用认证和 TLS。
- **最小权限运行时** - 主控端和代理端都以 `dockflare` 用户（UID/GID 65532）运行，并且只通过随附的 socket proxy 与 Docker 通信，尽量缩小暴露的 API 面。

## 5. 身份验证与授权

- **强化界面登录** - 初始设置向导会强制创建管理员账户。虽然可以禁用密码登录，但考虑到 Docker 网络层面的安全风险，**强烈不建议这样做**。
- **会话管理** - Flask-Login 会话与加密配置绑定。恢复备份或轮换凭据后，现有会话会自动失效。
- **Agent ACL** - 每条 Agent 记录都会跟踪隧道分配、心跳时间戳和待执行命令。主控端只会向提交正确令牌且已登记的 Agent 下发命令。

### ⚠️ 重要提示："Disable Password Login" 安全警告

DockFlare 提供 “Disable Password Login” 设置，适用于由外部身份验证层（例如 Cloudflare Access）保护 DockFlare 的高级部署场景。**对于大多数部署，我们强烈不建议启用此功能**。

**启用后的安全风险：**
- **所有 API 端点都会在无身份验证的情况下暴露**
- **Docker 网络暴露风险：** 即使 DockFlare 在公网侧由 Cloudflare Access 保护，同一 Docker 网络中的其他容器仍可能绕过外部认证，直接访问 DockFlare API
- **应用层不再执行认证：** 应用会默认由外部系统完全负责安全控制

**攻击路径示例：**
```
Internet → Cloudflare Access (Protected) → DockFlare ✅
         ↓
Docker Network → Other Container → DockFlare API (Unprotected) ❌
```

**推荐做法：**
不要关闭密码认证，而应使用以下安全选项之一：
1. **DockFlare 本地凭据** - 使用 DockFlare 内置的用户名和密码认证
2. **OAuth/OIDC 提供程序** - 配置 Google、GitHub、Azure AD 或其他身份提供商，在不牺牲安全性的前提下实现单点登录

这两种方式都能提供完整的身份验证能力，同时保留 SSO 的便利性。使用 OAuth 可以获得单点登录体验，而不会引入关闭认证带来的风险。

**结论：** 除非你拥有非常明确、经过充分验证并且具备网络隔离的安全架构，否则应保持密码登录开启，并使用 OAuth 提升登录体验。

## 6. 审计与运维可见性

- **元数据追踪** - Agent 密钥会记录 `created_at`、`last_used_at`、`bound_agent_id`、状态和吊销事件。`state.json` 也会反映代理端最近一次联机时间，便于快速健康检查。
- **日志流** - 实时日志通过 Redis 发布/订阅传输。敏感值（令牌、密钥）会在发送到客户端前被遮蔽。
- **状态 API** - `/api/v2/overview` 汇总隧道、代理端和配置的健康状态，可供监控系统或 GitOps 工作流使用。

## 7. 部署建议

| 区域 | 建议 |
| --- | --- |
| Docker 卷 | 持久化 `/app/data`（加密配置、密钥、状态）。如果启用了文件日志，也保留 `/app/logs`，并确保宿主机挂载目录可由 UID/GID 65532 或自定义构建参数写入。 |
| Redis | 在私有网络（`dockflare-internal`）中与 DockFlare 一起运行 `redis:7-alpine`，或让 `REDIS_URL` 指向已启用认证和 TLS 的实例。避免将 Redis 直接暴露到公网。使用 `REDIS_DB_INDEX` 将 DockFlare 数据与同一 Redis 实例中的其他容器隔离。 |
| 备份 | 定期下载 `.zip`，并与 `dockflare.key` 一起妥善保存。恢复时解密配置需要这两个文件。 |
| Agent | 将 API 密钥视为敏感凭据。使用 socket proxy 部署代理端，仅暴露必需的 Docker 端点，并记住容器以非特权 `dockflare` 用户（UID/GID 65532）运行；必要时对齐宿主机权限或使用匹配的 `DOCKFLARE_UID/DOCKFLARE_GID` 重新构建。 |
| 反向代理 | 将 DockFlare 放在 Cloudflare Access 或其他可信 IdP 后面。如果关闭密码登录，必须确保上游身份验证始终生效。 |
| 监控 | 针对异常重启、代理心跳中断或维护窗口之外的新密钥签发配置告警。 |

## 8. 后续增强（路线图）

- 为静态 Fernet 密钥提供可选的额外口令保护。
- 支持带宽限期的 Agent 密钥自动轮换，以便分阶段部署。
- 提供更细粒度的 Agent 命令权限范围，用于区分只读操作和变更操作。

---

DockFlare 会持续改进安全性。请关注发行说明中的后续加固更新；如果您需要额外的控制能力，也欢迎通过 issue tracker 提出建议。
