# DockFlare 代理与多服务器架构

DockFlare 3.0 引入了分布式架构，让您能够跨多台 Docker 主机统一管理 Cloudflare 隧道。DockFlare **主控端（Master）** 负责协调配置，而轻量级 **代理端（Agent）** 则部署在各个工作负载所在的主机上，并保持本机 `cloudflared` 实例与主控端同步。

本文介绍代理模式下的整体架构、安全模型和部署流程。

---

## 为什么需要代理端？

* **将计算与入口流量控制解耦**：工作负载可以更靠近用户部署，而控制平面仍保持统一。
* **按主机查看状态**：您可以单独监控每个代理端的心跳、隧道状态和命令历史。
* **最小权限隔离**：可以单独撤销某个代理端，而不影响主控端或其他主机。
* **具备弹性**：即使主控端短暂不可用，代理端仍会继续使用上一次已知配置提供服务。

---

## 组件概览

| 组件 | 职责 |
|-----------|----------------|
| **主控端（DockFlare）** | 托管管理界面、保存状态、协调目标入口规则并下发命令。 |
| **Redis** | 用于缓存、代理心跳和命令队列的后端通道。 |
| **DockFlare 代理端** | 无界面容器，负责监控本地 Docker 事件、执行命令并运行 `cloudflared`。 |
| **cloudflared** | 负责每个代理到 Cloudflare 的实际隧道连接。 |

主控端与 Redis 通常部署在一起，而代理端则部署在业务主机旁边，也可以位于远程网络中。

---

## 前置条件

* DockFlare 主控端版本需为 v3.0 或更高，并已配置 Redis（设置了 `REDIS_URL`）。如有需要，也可以设置 `REDIS_DB_INDEX`，以便与同一 Redis 实例上的其他容器隔离数据。
* 具备 Tunnel + Access 权限的 Cloudflare API 令牌，与之前版本相同。
* 您计划管理的每台主机上都需要有 Docker 运行时。
* （可选）如果您不打算直接暴露主控端，请在主控端与代理端之间使用专用网段或 VPN。

---

## 工作流程概览

1. **在 DockFlare 管理界面中生成代理 API 密钥**（`Agents → Generate Key`）。
2. **在远程主机上部署 DockFlare 代理端**，并传入主控端 URL 和密钥。
3. 代理端会向主控端**注册**，并显示为 *Pending* 状态。
4. 在主控端界面中**完成注册**，并为该主机分配或创建 Cloudflare 隧道。
5. 主控端将命令写入队列；代理端会**轮询**、应用配置并回报状态与心跳。DockFlare 会自动检测每个主机名所属的目标区域，只有检测失败时才会回退到默认区域。
6. 当代理主机上的容器启动或停止时，代理端会将事件流式回传给主控端，由主控端更新 DNS、Access 策略和隧道入口规则。

---

## 部署 DockFlare 代理端

> ℹ️ 该镜像将以 `alplat/dockflare-agent` 的名称发布。在公共仓库上线之前，您可以直接从 DockFlare 3.0 附带的 `DockFlare-agent` 源码目录构建。

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

代理主机上的最小 `docker-compose.yml` 示例：

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

- 运行一次 `docker network create cloudflare-net`，为主控端和代理端准备共享网络。
- Socket proxy 会限制代理端可访问的 Docker API 范围；只有设为 `1` 的能力才会开放。
- 代理镜像以非特权用户 `dockflare`（UID/GID 65532）运行。请确保 `/app/data` 等挂载目录对该用户可写，或者使用 `DOCKFLARE_UID/DOCKFLARE_GID` 重新构建以匹配宿主机权限。
- 在 `.env` 文件中填写 `DOCKFLARE_MASTER_URL` 和 `DOCKFLARE_API_KEY`；也可以用同样的方式提供可选覆盖项，例如 `LOG_LEVEL` 或 `DOCKER_HOST`。

---

## 安全模型

* **Master API 密钥**：用于保护管理 API。只有在您点击 *Show master API key* 之后，界面才会显示它。
* **Agent API 密钥**：每个代理端都有独立密钥。撤销后，该主机会立刻失去注册和接收命令的能力。
* **Redis**：用于队列和缓存；如果运行在不受信任的局域网之外，请启用密码保护并配置网络访问控制。
* **传输层**：建议将主控端部署在 HTTPS 之后，例如配合 Cloudflare Access，确保代理流量全程加密。
* **最小权限运行时**：代理容器以 `dockflare` 用户（UID/GID 65532）运行，并通过 socket proxy 将 Docker 的访问范围限制在必要能力内。

### 建议的加固措施

1. 将 Agent 密钥保存在密码管理器或密钥库中，并定期轮换。
2. **不要禁用密码登录**。请改用 OAuth/OIDC 提供程序，以获得 SSO 的便利而不牺牲安全性。如果您必须禁用密码登录，需要明白这会带来 Docker 网络层面的安全漏洞，同一网络中的任意容器都可能绕过外部认证。有关完整安全影响，请参阅 [访问网页管理界面](Accessing-the-Web-UI.md)。
3. 为每个代理端使用单独的隧道，以实现更好的最小权限隔离。
4. 监控 `Agents` 页面中的心跳间隔；离线节点可以直接从界面中移除。

---

## 故障排除

| 症状 | 解决方法 |
|---------|-----|
| Agent 卡在 `pending` | 确认它使用了正确的 API 密钥完成注册，并在界面中批准入驻。 |
| 命令一直不清空 | 检查 Redis 连通性，并确认代理容器的时钟已同步。 |
| DNS 未更新 | 主控端必须能够连接 Cloudflare，代理端也必须发送容器事件；请检查 `docker logs dockflare-agent`。 |
| Heartbeat 离线 | 检查代理端与主控端之间的网络路径；防火墙或 TLS 问题很常见。 |

---

## 后续步骤

* 查看仓库 README 中更新后的快速开始说明，确认 Redis 已正确配置。
* 查看更新日志，了解破坏性变更和迁移说明。
* 等 DockFlare Agent 公共仓库发布后订阅它，以便及时掌握新版本。

祝您使用顺利。
