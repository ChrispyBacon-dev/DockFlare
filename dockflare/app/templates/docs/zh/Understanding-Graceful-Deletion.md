# 理解优雅删除

当您停止由 DockFlare 管理的容器时，您可能会注意到其相应的公共主机名不会立即离线。这是由于一项名为 **Graceful Deletion** 的功能所致。

## 什么是优雅删除？

DockFlare 不会在容器停止时立即删除 Cloudflare 入口规则和 DNS 记录，而是将该规则标记为 **“待删除”** 并启动计时器。

关联的 Cloudflare 资源（入口规则和 DNS 记录）仅在此计时器（称为 **宽限期**）到期后才会被永久删除。

## 为什么这很有用？

此功能旨在防止常见操作场景中的服务中断：

* **容器更新：** 当您更新容器映像 (`docker compose up -d`) 时，Docker 通常会停止旧容器并启动一个新容器。如果没有宽限期，您的服务将在短时间内无法访问。通过优雅删除，DNS 记录和入口规则保持活动状态，DockFlare 只需将它们与新容器重新关联，从而实现零停机。
* **临时重新启动：** 如果您需要暂时停止容器以更改设置然后重新启动它，宽限期可确保您面向公众的配置保持不变。

## `GRACE_PERIOD_SECONDS` 变量

此宽限期的持续时间由 `GRACE_PERIOD_SECONDS` 环境变量控制，您可以在 `docker-compose.yml` 文件中设置该变量。

* 默认值为 `600` 秒（10 分钟）。
* 您可以调整该值以满足您的需要。较短的周期使清理速度更快，而较长的周期则为容器重新启动提供了更大的窗口。

**示例：**
```yaml
services:
  dockflare:
    image: alplat/dockflare:stable
    # ... other settings
    environment:
      - GRACE_PERIOD_SECONDS=3600 # Set a 1-hour grace period
```

## 它在实践中是如何运作的

1. **容器已停止：** 您运行 `docker stop my-app`。
2. **待删除：** DockFlare 检测到停止事件。在网页管理界面中，`my-app.example.com` 的规则会显示其状态为 **“pending_deletion”**，并标出计划删除的时间。
3. **两种情况：**
    * **场景 A：宽限期到期：** 如果容器保持停止状态并且宽限期（例如 10 分钟）到期，DockFlare 的后台清理任务将运行。它将从您的 Cloudflare 隧道中删除入口规则并删除 CNAME DNS 记录。
    * **场景 B：容器重新启动：** 如果您再次启动容器 (`docker start my-app`) **在宽限期到期之前**，DockFlare 将检测启动事件。它将看到该规则正在等待删除，取消删除，并将其状态更改回 **“活动”**。您的服务将继续无缝运行。
