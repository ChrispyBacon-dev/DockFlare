# 调试和日志

在对 DockFlare 问题进行故障排除时，您的主要工具是 DockFlare 容器及其托管 `cloudflared` 代理生成的日志。

## 1. 检查 DockFlare 容器日志

最重要的信息来源是 DockFlare 容器本身的日志输出。这些日志提供了 DockFlare 正在执行的操作的详细实时视图。

### 您将在日志中找到什么：
* 检测 Docker 容器启动/停止事件。
* `dockflare.*` 标签的处理。
* 正在调用 Cloudflare API。
* 来自 Cloudflare API 的成功消息或详细错误响应。
* 资源清理等后台任务的状态。

### 如何查看日志：
要查看日志，请在终端中使用以下 Docker 命令：
```bash
# View the full log history
docker logs dockflare

# Follow the logs in real-time
docker logs -f dockflare
```

## 2. 使用网页管理界面的实时日志

为了方便起见，DockFlare 仪表板在主页底部包含一个**实时日志查看器**。

此查看器流式传输的日志与您使用 `docker logs -f dockflare` 看到的日志完全相同，但提供了一种无需离开浏览器即可查看当前正在发生的情况的简单方法。这对于观察 DockFlare 在启动或停止容器后立即执行的操作特别有用。

## 3. 检查 `cloudflared` 代理日志

如果您怀疑问题出在服务器和 Cloudflare 网络之间的连接上，您可以直接检查 `cloudflared` 代理容器的日志。

### 如何查看代理日志：
首先，您需要找到代理容器的名称。默认情况下，它被命名为 `cloudflared-agent-<tunnel-name>`，其中 `<tunnel-name>` 是在 DockFlare 设置中配置的隧道的名称。

您可以使用 `docker ps` 找到确切的名称。

获得名称后，运行：
```bash
# Replace with the actual container name
docker logs cloudflared-agent-dockflare-tunnel
```

这些日志对于诊断很有用：
* Cloudflare 边缘的连接错误。
* 您的隧道令牌的身份验证问题。
* 被代理的流量的协议级错误。

**注意：** 这仅适用于您使用默认的**内部模式**。如果您使用[外部模式](External-cloudflared-Mode.md)，则需要检查您自己的 `cloudflared` 代理进程的日志。

## 4. 检查 Cloudflare 仪表板

最后，不要忘记使用 Cloudflare 仪表板作为调试工具。
* **DNS 页面：** 检查 CNAME 记录是否按照您的预期创建。
* **零信任仪表板：** 转到 **访问 -> 隧道** 以检查隧道的状态及其入口规则。
* **零信任仪表板：** 转至 **访问 -> 应用程序** 检查零信任策略的配置和运行状况。策略的“上次查看”状态可以提供非常丰富的信息。
