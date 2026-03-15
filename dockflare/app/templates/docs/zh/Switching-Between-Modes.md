# 模式切换

您可以随时在 **Internal**（默认）和 **External** `cloudflared` 模式之间切换 DockFlare。本指南解释了平稳过渡的过程。

有关两种模式的详细比较，请参阅 [内部与外部 `cloudflared`](Internal-vs-External-cloudflared.md) 页面。

---

## 从内部模式切换到外部模式

此过程涉及设置您自己的 `cloudflared` 代理，然后告诉 DockFlare 使用它。

**步骤 1：设置您的外部 `cloudflared` 代理**

首先，您需要设置并运行您自己的 `cloudflared` 代理。这可能是主机操作系统或另一个 Docker 容器上的进程。

* 确保将其配置为使用特定的 Cloudflare 隧道。
* 记下 **隧道 ID** (UUID)。
* 启动代理并确认其正常运行并在 Cloudflare 仪表板中显示为“已连接”。

**步骤 2：重新配置并重新启动 DockFlare**

接下来，您需要更新 DockFlare 容器的环境变量以告诉它切换到外部模式。

在您的 `docker-compose.yml` 中：
```yaml
services:
  dockflare:
    image: alplat/dockflare:stable
    # ... other settings
    environment:
      # Enable external mode
      - USE_EXTERNAL_CLOUDFLARED=true
      # Provide the ID of your running tunnel
      - EXTERNAL_TUNNEL_ID=your-tunnel-uuid-goes-here
```

**第 3 步：部署变更**

运行 `docker compose up -d` 以使用新的环境变量重新创建 DockFlare 容器。

当更新的 DockFlare 容器启动时：
1. 它将检测到 `USE_EXTERNAL_CLOUDFLARED` 是 `true`。
2. 它将**停止并删除**其自己的托管 `cloudflared-agent` 容器。
3. 它将开始将其所有入口规则配置发送到 `EXTERNAL_TUNNEL_ID` 指定的隧道。

您的服务现在将由您的外部管理的 `cloudflared` 代理提供。

---

## 从外部模式切换到内部模式

这个过程更简单，因为它涉及让 DockFlare 收回控制权。

**第 1 步：重新配置 DockFlare**

从 DockFlare `docker-compose.yml` 文件中删除外部模式环境变量。

```yaml
services:
  dockflare:
    image: alplat/dockflare:stable
    # ... other settings
    environment:
      # Remove the following two lines
      # - USE_EXTERNAL_CLOUDFLARED=true
      # - EXTERNAL_TUNNEL_ID=your-tunnel-uuid-goes-here
```

**第 2 步：部署变更**

运行 `docker compose up -d` 以重新创建 DockFlare 容器。

当更新的 DockFlare 容器启动时：
1. 它将检测到 `USE_EXTERNAL_CLOUDFLARED` 是 `false`。
2. 它将自动**创建、配置和启动**其自己的内部`cloudflared-agent` 容器。
3. 它将配置这个新代理以使用 DockFlare 设置中定义的隧道名称。

**步骤 3：停用您的外部代理**

一旦您确认新的内部代理正确运行并提供流量，您就可以安全地停止并删除您自己的 `cloudflared` 代理。
