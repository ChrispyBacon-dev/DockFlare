# 基本用法（单域）

本指南演示了 DockFlare 最常见的用例：通过公共主机名向互联网公开单个 Docker 容器。

## 先决条件

在开始之前，请确保您拥有：
1. 完成 [快速入门](Quick-Start-Docker-Compose.md) 指南。
2. DockFlare 正在运行并连接到您的 Cloudflare 帐户。
3. 您有一个想要公开的服务（在本例中我们将使用 `nginx`）。

## 示例：公开 NGINX 容器

假设您想要在主机名 `nginx.example.com` 处公开标准 NGINX Web 服务器。

### 1. 将服务添加到您的 `docker-compose.yml`

修改您的 `docker-compose.yml` 文件以包含 `nginx` 服务。关键是将 `dockflare.*` 标签添加到其配置中。

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
      - INFO=1
      - EXEC=1
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock
    networks:
      - dockflare-internal

  dockflare-init:
    image: alpine:3.20
    command: ["sh", "-c", "chown -R 65532:65532 /app/data"]
    volumes:
      - dockflare_data:/app/data
    networks:
      - dockflare-internal
    restart: "no"

  dockflare:
    image: alplat/dockflare:stable
    container_name: dockflare
    restart: unless-stopped
    ports:
      - "5000:5000"
    volumes:
      - dockflare_data:/app/data
    environment:
      - REDIS_URL=redis://redis:6379/0
      - REDIS_DB_INDEX=0  # Optional: specify Redis database index (0-15) for isolation from other containers
      - DOCKER_HOST=tcp://docker-socket-proxy:2375
    depends_on:
      docker-socket-proxy:
        condition: service_started
      dockflare-init:
        condition: service_completed_successfully
      redis:
        condition: service_started
    networks:
      - cloudflare-net
      - dockflare-internal

  # Add your new service here
  nginx-webserver:
    image: nginx:latest
    container_name: my-nginx
    restart: unless-stopped
    networks:
      - cloudflare-net
    labels:
      - "dockflare.enable=true"
      - "dockflare.hostname=nginx.example.com"
      - "dockflare.service=http://nginx-webserver:80"
      # Optional: Apply public access with zone protection bypass
      - "dockflare.access.group=public-default-bypass"

  redis:
    image: redis:7-alpine
    container_name: dockflare-redis
    restart: unless-stopped
    command: ["redis-server", "--save", "", "--appendonly", "no"]
    volumes:
      - dockflare_redis:/data
    networks:
      - dockflare-internal

volumes:
  dockflare_data:
  dockflare_redis:

networks:
  cloudflare-net:
    name: cloudflare-net
    external: true
  dockflare-internal:
    name: dockflare-internal
```
> **为什么选择 Redis？** DockFlare 依赖 Redis 进行缓存、日志流和跨线程消息传递。在私有 `dockflare-internal` 网络上运行它使 Redis 只能通过 DockFlare 访问，而工作负载在 `cloudflare-net` 上保持隔离。


### 2. 理解标签

* `dockflare.enable=true`：这告诉 DockFlare 管理这个容器。
* `dockflare.hostname=nginx.example.com`：这是您的服务可用的公共 URL。DockFlare 将在您的 Cloudflare 帐户中为此主机名创建一条 DNS 记录。
* `dockflare.service=http://nginx-webserver:80`：这告诉 Cloudflare Tunnel 将流量发送到哪里。它是 NGINX 容器的内部地址。请注意，我们使用服务名称 (`nginx-webserver`) 作为主机名，这是可能的，因为两个容器位于同一 Docker 网络上。
* `dockflare.access.group=public-default-bypass`：（可选）即使存在区域级 `*.example.com` 保护策略，也使用系统旁路策略来确保公共访问。当您有通配符策略保护您的域但需要特定服务来保持公开时，这一点非常重要。

### 3. 部署服务

保存 `docker-compose.yml` 文件并运行以下命令来启动新服务：

```bash
docker compose up -d
```

### 4. 验证

DockFlare 将检测新容器并自动执行以下操作：
1. 将 `nginx.example.com` 的入口规则添加到您的 Cloudflare Tunnel。
2. 在 Cloudflare DNS 中为 `nginx.example.com` 创建 CNAME 记录，指向隧道。

您可以通过几种方式验证这一点：
* **DockFlare 网页管理界面**：`nginx.example.com` 服务将出现在仪表板上。
* **Cloudflare 仪表板**：您将在 DNS 设置中看到新的 CNAME 记录，并在隧道配置中看到新的入口规则。

DNS 传播一段时间后，您应该能够在浏览器中导航到 `https://nginx.example.com` 并看到默认的 NGINX 欢迎页面。

## 备份和恢复深入探讨

DockFlare 附带一流的备份流程，因此您可以在几分钟内移动或恢复实例。

### 备份归档包含什么

当您从 **Settings → Backup & Restore**（或入门向导）下载备份时，DockFlare 会生成包含以下文件的 `.zip`：

| 文件 | 描述 |
| --- | --- |
| `dockflare_config.dat` | 加密配置负载（Cloudflare 凭证、界面密码哈希、隧道默认值、Master API 密钥等）。 |
| `dockflare.key` | 用于解密 `dockflare_config.dat` 与其他加密负载的 Fernet 密钥。请与归档一起保存。 |
| `agent_keys.dat` | Agent API 密钥、元数据与吊销状态的加密注册表。 |
| `state.json` | 运行时状态的明文 JSON 快照（托管规则、代理端、访问组）。包含该文件是为了便于运维人员检查或在需要时迁移部分状态。 |
| `manifest.json` | 存档中每个文件的校验和与版本信息。 |

备份是自包含的：通过向导/上传端点恢复时，会将每个文件写入 `/app/data/`，并立即安排容器重启，以便在启动时重新加载加密配置。

### 恢复和兼容性说明

- **向导和设置界面**：上传 `.zip` 后，DockFlare 会导入它、重新加载状态，然后退出。Docker 会自动重启容器，因此您无需手动干预即可恢复运行。
- **旧版 `state.json`**：用于故障排除或高级工作流程时，仍可仅上传 `state.json`。DockFlare 会从中填充运行时状态，但会跳过加密配置；之后您必须重新输入凭据。
- **自动化**：由于重新启动是自动的，因此请确保任何反向代理运行状况检查都允许恢复后短暂的重新启动窗口（约 5 秒）。

备份**不**包括 Redis 数据集；它只缓存 DockFlare 可以重新计算的数据。 `/app/data` 卷与存档一起是保护和备份的关键部分。
