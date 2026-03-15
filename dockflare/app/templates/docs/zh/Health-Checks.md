# 健康检查

DockFlare 包含一个专用的健康检查端点，可以与 Docker 的内置健康检查机制一起使用。这使得 Docker 能够监控 DockFlare 应用程序的运行状况，并在它变得无响应时自动重新启动它。

## `/ping` 端点

DockFlare 在 `/ping` 处公开了一个简单的 HTTP 端点。

* **目的：** 为自动化系统提供一种简单的方法来检查 DockFlare Web 服务器是否正在运行且响应。
* **身份验证：** 此端点 **免于身份验证**。您无需登录即可访问它，这使得 Docker 的内部健康检查机制可以使用它。
* **健康响应：** 健康、运行的 DockFlare 应用程序将使用 **HTTP 200 OK** 状态代码响应 `/ping` 处的请求。
* **版本信息：** 来自 `/ping` 端点的响应正文还包含 DockFlare 应用程序的运行版本。

## 如何在 Docker Compose 中配置健康检查

您可以将 `healthcheck` 部分添加到 `docker-compose.yml` 文件中的 `dockflare` 服务中，以使 Docker 自动监视应用程序的运行状况。

```yaml
services:
  dockflare:
    image: alplat/dockflare:stable
    container_name: dockflare
    restart: unless-stopped
    # ... other settings
    healthcheck:
      # The command to run to check health.
      # curl is used to make an HTTP request to the ping endpoint.
      test: ["CMD", "curl", "-f", "http://localhost:5000/ping"]
      # How often to run the check
      interval: 1m30s
      # How long to wait for a response
      timeout: 10s
      # How many consecutive failures before marking as unhealthy
      retries: 3
      # How long to wait after the container starts before running the first check
      start_period: 40s
```

### `healthcheck` 配置的细分：

* `test`：这是 Docker 在容器内运行的命令。`curl -f` 将向 `/ping` 端点发出 HTTP 请求，如果响应不是 HTTP 200 OK，则将以非零状态代码退出。
* `interval`：Docker 将每 90 秒运行一次此检查。
* `timeout`：Docker 将等待最多 10 秒以完成命令。
* `retries`：如果连续3次检查失败，Docker会将容器标记为`unhealthy`。
* `start_period`：Docker 将在容器启动后等待 40 秒，然后再执行第一次运行状况检查。这使得应用程序有时间正确初始化。

完成此配置后，您可以通过运行 `docker ps` 检查容器的运行状况。如果健康检查通过，状态列将显示 `(healthy)`。如果容器变得不健康，Docker 将根据 `restart` 策略（例如 `unless-stopped`）自动重新启动它。
