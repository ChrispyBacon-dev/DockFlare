# 快速入门（Docker Compose）

本指南介绍如何使用强化的 socket proxy 与 rootless 主控端配置，以最快方式运行 DockFlare。

### 1. 创建 `docker-compose.yml` 文件

下面的编排会启动 `docker-socket-proxy`，用正确的权限初始化持久化卷，并与 Redis 一起启动 DockFlare。

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

**注意事项：**
- 主控端容器以 `dockflare` 用户（UID/GID 65532）运行。如果需要匹配不同的主机权限，请设置 `DOCKFLARE_UID`/`DOCKFLARE_GID` 并重建镜像，或调整初始化任务。
- Socket proxy 是必需的。DockFlare 从不直接挂载 `/var/run/docker.sock`，以严格限制主控端可访问的 Docker API 暴露面。
- 如果使用 bind mount 而不是 named volume，请确保目标目录可由 UID/GID 65532（或您覆盖后的值）写入。
- 如果外部网络不存在，则创建一次：`docker network create cloudflare-net`。

### 2.运行 DockFlare

以分离模式启动服务栈：

```bash
docker compose up -d
```

这将启动代理、启动卷并与 Redis 一起启动 DockFlare。

### 3. 完成首次设置

服务运行后，打开浏览器并访问 `http://<your-server-ip>:5000`。

**初始设置向导**将引导您完成：
1. 为网页管理界面创建密码。
2. 输入您的 Cloudflare 凭据（帐户 ID、区域 ID、API 令牌）。
3. 配置您的初始 Cloudflare 隧道。
4. *（可选）* 从 DockFlare 备份存档中恢复。如果您已有 `dockflare_backup_*.zip`，请在步骤 1 之前选择 `Restore from backup`（从备份恢复）；向导会导入配置并自动重启容器。

### 4. 对于现有用户（升级）

如果您从旧版本升级，DockFlare 会检测旧版 `.env` 文件，将配置迁移到加密存储中，并引导您完成密码创建。请保留 socket proxy，因为不再支持直接挂载 `/var/run/docker.sock`。
