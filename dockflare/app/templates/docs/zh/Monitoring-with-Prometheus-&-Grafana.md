# 使用 Prometheus 和 Grafana 进行监控

DockFlare 管理的 `cloudflared` 代理可以以 Prometheus 格式公开各种性能和运行状况指标。通过收集和可视化这些指标，您可以获得有关隧道流量、延迟和错误率的宝贵见解。

本指南介绍了如何启用指标端点，并提供使用 Prometheus 和 Grafana 的监控堆栈的快速设置。

## 步骤 1：在 DockFlare 中启用 Metrics 端点

第一步是告诉 DockFlare 在其托管 `cloudflared` 代理上启用 Prometheus 指标端点。

您可以通过为 DockFlare 容器设置 `CLOUDFLARED_METRICS_PORT` 环境变量来完成此操作。

**示例 `docker-compose.yml`:**
```yaml
services:
  dockflare:
    image: alplat/dockflare:stable
    # ... other settings
    environment:
      # Enable the metrics endpoint on port 2000 inside the container
      - CLOUDFLARED_METRICS_PORT=2000
```
当您使用此变量重新启动 DockFlare 时，它将自动重新创建其托管 `cloudflared` 代理，并在指定端口上启用指标服务器。

**注意：** 此功能仅在默认的 **内部模式** 下可用。如果您使用[外部模式](External-cloudflared-Mode.md)，则您负责在自己的 `cloudflared` 代理上启用指标端点。

## 步骤 2：设置监控堆栈

如果您还没有监控堆栈，可以使用 Docker Compose 快速设置一个。DockFlare 仓库在 `/examples` 目录中提供了示例设置。

有关如何设置 Prometheus 和 Grafana 来监控 DockFlare 的完整复制粘贴指南，请参阅仓库中的 **[`grafana quick setup.md`](https://github.com/ChrispyBacon-dev/DockFlare/blob/main/examples/grafana%20quick%20setup.md)** 文件。

本指南将引导您完成：
1. 创建必要的目录结构。
2. 将 Prometheus 和 Grafana 服务添加到您的 `docker-compose.yml` 中。
3. 配置 Prometheus 从 `cloudflared` 代理中抓取指标。
4. 自动为 Grafana 配置 Prometheus 数据源。

## 步骤 3：导入预制的 Grafana 仪表板

为了使可视化变得简单，DockFlare 提供了一个预制的 Grafana 仪表板，该仪表板旨在与 `cloudflared` 代理公开的指标完美配合。

1. 仪表板在存储库的 `/examples` 目录中以 **[`dashboard.json`](https://github.com/ChrispyBacon-dev/DockFlare/blob/main/examples/dashboard.json)** 形式提供。
2. 下载该文件。
3. 登录您的 Grafana 实例。
4. 转到“仪表板”部分并单击“导入”。
5. 上传`dashboard.json` 文件。
6. 选择您的 Prometheus 数据源并导入仪表板。

您现在将全面了解 Cloudflare Tunnel 的性能，包括请求计数、错误率、连接延迟等。

![Grafana 仪表板示例](../static/images/grafana_dashboard_example.png)
