# 常见问题

本页列出了用户可能遇到的一些常见问题以及解决方法。

---

### 问题：DockFlare 容器无法启动或处于重新启动循环中。

**解决方案：**
1. **检查 Docker 日志：** 第一步始终是检查 DockFlare 容器的日志。运行以下命令：
    ```bash
    docker logs dockflare
    ```
2. **查找错误：** 查找任何错误消息。常见原因包括：
    * 无效的 `docker-compose.yml` 文件（例如，语法不正确、卷安装问题）。
    * Docker 守护进程本身的问题。
    * docker-socket-proxy 服务或 `DOCKER_HOST` 设置的连接或权限问题。

---

### 问题：未在 Cloudflare 中创建 DNS 记录。

**解决方案：**
1. **检查 DockFlare 日志：** 查找与 Cloudflare API 相关的任何错误消息。日志通常会告诉您 API 调用失败的确切原因。
2. **验证 API 令牌权限：** 这是最常见的原因。确保您的 Cloudflare API 令牌具有所需的权限。至少，您需要：
    * `Zone:DNS:Edit` 用于您希望 DockFlare 管理的每个区域。
    * `Zone:Zone:Read`
3. **验证区域配置：**
    * 确保您在设置过程中提供的 **区域 ID** 正确。
    * 如果您使用 `dockflare.zonename` 标签，请仔细检查区域名称拼写是否正确。

---

### 问题：访问策略（零信任）未应用于服务。

**解决方案：**
1. **检查 API 令牌权限：** 确保您的 API 令牌具有 `Account:Access: Apps and Policies:Edit` 权限。
2. **检查界面覆盖：** 在 DockFlare 仪表板中，检查规则是否具有“界面覆盖”状态。界面覆盖优先于标签。
3. **检查访问组 ID：** 如果您使用 `dockflare.access.group`，请确保您在标签中指定的 ID **完全** 与您在“访问策略”页面上为访问组创建的 ID 匹配。
4. **检查 Cloudflare 仪表板：** 登录到您的 Cloudflare 零信任仪表板。导航到 **Access -> 应用程序** 以查看是否已创建 Access 应用程序。有时，Cloudflare 会显示一个在 API 响应中不可见的错误。

---

### 问题：我在尝试访问我的服务时收到 `ERR_TOO_MANY_REDIRECTS` 错误。

**解决方案：**
此错误几乎总是由于源服务和 Cloudflare 之间的 SSL/TLS 设置配置错误而发生。

1. **检查 Cloudflare SSL/TLS 模式：** 在 Cloudflare 仪表板中，转到您的域的 SSL/TLS 设置。确保您的加密模式设置为 **完全（严格）**。
2. **避免双重重定向：** 如果您的后端应用程序也尝试从 HTTP 重定向到 HTTPS，则 Cloudflare 中的“灵活”SSL 模式可能会导致此问题。浏览器陷入循环。
3. **在您的服务 URL 中使用 `https`：** 如果您的后端服务支持 HTTPS，请在 `dockflare.service` 标签中使用 `https://`（例如 `dockflare.service=https://my-app:443`）。这可确保从 `cloudflared` 到您的服务的连接也是加密的。

---

### 问题：Traefik/Proxmox 背后的服务仅在启用 Cloudflare 的“将 SNI 与主机匹配”时才起作用。

**解决方案：**
1. 在 DockFlare 中编辑手动规则并启用 **将 SNI 与主机匹配**。
2. 保存规则并在 Cloudflare 零信任中验证路由。
3. 如果您还需要 DockFlare 保留 DockFlare 未建模的 Cloudflare 端路由字段，请转到 **设置 → 常规设置** 并启用 **保留非托管 Cloudflare 入口字段**。

---

### 问题：托管 `cloudflared-agent` 容器无法启动，并出现“失效网络”错误。

**解决方案：**
如果代理使用的 Docker 网络被删除并重新创建，则可能会发生这种情况。DockFlare 旨在自动处理此问题。

1. **重新启动 DockFlare：** 简单地重新启动 DockFlare 容器 (`docker compose restart dockflare`) 即可解决此问题。
2. **工作原理：** 启动时，DockFlare 会检查其托管代理的运行状况。如果检测到这一特定问题，它将自动删除损坏的代理容器并创建一个具有正确配置的新容器。这是版本 `v1.9.5` 中修复的特定错误。确保您使用的是最新版本的 DockFlare。
