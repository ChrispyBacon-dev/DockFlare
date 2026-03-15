# DockFlare Agent 与多服务器架构

DockFlare 3.0 引入了分布式执行模型，让您可以跨多个 Docker 主机管理 Cloudflare 隧道。DockFlare **Master** 负责协调配置，而轻量级 **Agent** 会与工作负载一起运行，并保持各主机上的 `cloudflared` 实例与 Master 同步。

本指南介绍部署代理时涉及的架构、安全模型和分步工作流程。

---

## 为什么需要 Agent？

* **将计算与 ingress 解耦**：让工作负载更接近用户，同时保留统一的控制平面。
* **按主机查看状态**：监控每个 Agent 的 heartbeat、隧道状态和命令历史。
* **最小权限令牌**：在不影响 Master 或其他主机的情况下撤销受影响的 Agent。
* **具备弹性的更新**：如果 Master 暂时不可用，代理仍会使用最后一次已知配置继续提供流量。

---

## 组件概览

| 组件 | 职责 |
|-----------|----------------|
| **Master（DockFlare）** | 托管 Web UI、保存状态、协调期望的 ingress 规则并下发命令。 |
| **Redis** | 用于缓存、Agent heartbeat 和排队命令的 backplane。 |
| **DockFlare Agent** | 无界面容器，负责监控本地 Docker 事件、执行命令并运行 `cloudflared`。 |
| **cloudflared** | 负责每个代理到 Cloudflare 的实际隧道连接。 |

Master 和 Redis 通常一起运行，而代理则部署在工作负载旁边，也可以位于远程网络。

---

## 前置条件

* DockFlare Master ≥ v3.0，并已配置 Redis（设置了 `REDIS_URL`）。可选地指定 `REDIS_DB_INDEX`，以便与使用同一 Redis 实例的其他容器隔离数据。
* 具备 Tunnel + Access 权限的 Cloudflare API 令牌，与之前版本相同。
* 您计划管理的每台主机上都需要有 Docker 运行时。
* （可选）如果您不打算公开暴露 Master，请在 Master 与代理之间使用专用网段或 VPN。

---

## 工作流程概览

1. **在 DockFlare UI 中生成代理 API 密钥**（`Agents → Generate Key`）。
2. **在远程主机上部署 DockFlare Agent** 容器，并传入 Master URL 和密钥。
3. 代理会向 Master **注册**，并显示为 *Pending* 状态。
4. 在 Master UI 中**完成注册**，并为该主机分配或创建 Cloudflare 隧道。
5. Master 将命令加入队列；代理会**轮询**、应用配置并回报状态与 heartbeat。DockFlare 会自动检测每个主机名对应的目标区域，只有在检测失败时才回退到默认区域。
6. 当代理主机上的容器启动或停止时，代理会将事件流式回传给 Master，由后者更新 DNS、Access 策略和隧道 ingress 规则。

---

## 部署 DockFlare Agent

> ℹ️ 该代理将以 `alplat/dockflare-agent` 的名称发布。在公共仓库上线之前，您可以从 DockFlare 3.0 附带的 `DockFlare-agent` 源代码树进行构建。

```bash
# Example environment file used by the agent container
DOCKFLARE_MASTER_URL=https://dockflare.example.com
DOCKFLARE_API_KEY=agent_api_key_goes_here
DOCKER_HOST=tcp://docker-socket-proxy:2375
# control the docker image used for the managed cloudflared tunnel (accepts repo:tag or repo@sha256:<digest>)
CLOUDFLARED_IMAGE=cloudflare/cloudflared:2025.9.0
LOG_LEVEL=info
TZ=Europe/Zurich
```

代理主机上的最小 `docker-compose.yml`：

```yaml
version: '3.8'

services:
  docker-socket-proxy:
    image: tecnativa/docker-socket-proxy:v0.4.1
    container_name: docker-socket-proxy
    restart: unless-stopped
    environment:
      - DOCKER_HOST=unix:///var/run/docker.sock
      - CONTAINERS=1
      - EVENTS=1
      - NETWORKS=1
      - IMAGES=1
      - POST=1
      - PING=1
      - EXEC=1
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock
    networks:
      - dockflare-internal
      
  dockflare-agent:
    image: alplat/dockflare-agent:latest
    container_name: dockflare-agent
    restart: unless-stopped
    env_file:
      - .env
    environment:
      - DOCKER_HOST=${DOCKER_HOST:-tcp://docker-socket-proxy:2375}
      - TZ=${TZ:-UTC}
      - LOG_LEVEL=${LOG_LEVEL:-info}
    volumes:
      - agent_data:/app/data
    depends_on:
      - docker-socket-proxy
    networks:
      - cloudflare-net
      - dockflare-internal

volumes:
  agent_data:

networks:
  cloudflare-net:
    name: cloudflare-net
    external: true
  dockflare-internal:
    name: dockflare-internal
```

- 运行一次 `docker network create cloudflare-net`，为 Master 和 Agent 准备共享网络。
- Socket proxy 会限制 Agent 可访问的 Docker API 范围；只有设置为 `1` 的能力会被公开。
- Agent 镜像以非特权用户 `dockflare`（UID/GID 65532）运行。请确保像 `/app/data` 这样的挂载目录对该账号可写，或者使用 `DOCKFLARE_UID/DOCKFLARE_GID` 重新构建以匹配您的主机。
- 在 `.env` 文件中填写 `DOCKFLARE_MASTER_URL` 和 `DOCKFLARE_API_KEY`；也可以用同样的方式提供可选覆盖项，例如 `LOG_LEVEL` 或 `DOCKER_HOST`。

---

## 安全模型

* **Master API 密钥**：用于保护管理 API。UI 只会在您点击 *Show master API key* 后显示它。
* **Agent API 密钥**：每个 Agent 唯一。撤销某个密钥会立即阻止该主机继续注册或接收命令。
* **Redis**：用于队列和缓存；如果运行在不受信任的 LAN 之外，请使用密码和网络 ACL 进行保护。
* **传输层**：建议将 Master 放在 HTTPS 之后运行，例如通过 Cloudflare Access，以确保代理流量被加密。
* **最小权限运行时**：Agent 容器以 `dockflare` 用户（UID/GID 65532）身份运行，并依赖 socket proxy 将 Docker 访问范围限制在容器检查和生命周期控制上。

### 建议的加固措施

1. 将 Agent 密钥保存在密码管理器或密钥库中，并定期轮换。
2. **不要禁用密码登录**。请改用 OAuth/OIDC 提供程序，以获得 SSO 的便利而不牺牲安全性。如果您必须禁用密码登录，需要明白这会带来 Docker 网络层面的安全漏洞，同一网络中的任意容器都可能绕过外部认证。有关完整安全影响，请参阅 [访问 Web UI](Accessing-the-Web-UI.md)。
3. 为每个 Agent 使用单独的隧道，以保持最小权限隔离。
4. 监控 `Agents` 页面中的 heartbeat 间隔；离线节点可以直接从 UI 中移除。

---

## 故障排除

| 症状 | 解决方法 |
|---------|-----|
| Agent 卡在 `pending` | 确认它使用正确的 API 密钥完成注册，并在 UI 中完成入驻。 |
| 命令一直不清空 | 检查 Redis 连通性，并确认代理容器的时钟已同步。 |
| DNS 未更新 | Master 必须能够连接 Cloudflare，Agent 也必须发送容器事件；请检查 `docker logs dockflare-agent`。 |
| Heartbeat 离线 | 检查 Agent 与 Master 之间的网络路径；防火墙或 TLS 问题是常见原因。 |

---

## 后续步骤

* 查看仓库 README 中更新后的 Quick Start，确认 Redis 已正确配置。
* 查看 changelog 了解破坏性变更和迁移说明。
* 等 DockFlare Agent 公共仓库发布后订阅它，以便及时了解新版本。

祝您 tunneling 顺利！ 🚇
