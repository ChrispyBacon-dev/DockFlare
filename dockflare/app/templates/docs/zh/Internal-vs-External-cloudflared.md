# 内部与外部 `cloudflared`

DockFlare 可以以两种模式运行来管理 `cloudflared` 代理，该代理实际上是在您的服务器和 Cloudflare 网络之间创建持久连接的软件。了解这两种模式是为您的环境选择正确设置的关键。

## 内部模式（默认）

在内部模式下，DockFlare 全面负责管理 `cloudflared` 代理。

### 它是如何运作的
当 DockFlare 启动时，它会自动：
1. 创建一个运行 `cloudflare/cloudflared` 映像的专用 Docker 容器。
2. 配置此代理容器以连接到您的 Cloudflare 帐户并使用 DockFlare 设置中指定的隧道。
3. 确保代理正在运行，如果失败则重新启动。
4. 自动应用任何相关设置，例如启用 Prometheus 指标端点。

对于大多数用户来说，这是**默认和推荐**模式。

### 优点
* **简单性：** 这是一个“零配置”设置。DockFlare 会为您处理一切。
* **保证兼容性：** DockFlare 确保代理以可以使用的方式配置。
* **集中管理：** 与隧道相关的所有内容均由 DockFlare 管理。

### 缺点
* **控制较少：** 除了 DockFlare 公开的内容之外，您对 `cloudflared` 代理配置的控制有限。

---

## 外部 `cloudflared` 模式

在外部模式下，您负责自行运行和管理 `cloudflared` 代理。DockFlare 将连接到此现有代理，而不是创建自己的代理。

### 它是如何运作的
DockFlare 将**不会**创建 `cloudflared` 容器。相反，它会假设您有一个 `cloudflared` 代理在它可以使用的地方运行。这可能是：
* 直接在主机操作系统上运行的 `cloudflared` 进程（例如，作为 `systemd` 服务）。
* 一个 `cloudflared` 容器，您可以使用单独的 `docker-compose.yml` 文件或 Docker 运行命令自行管理。
* `cloudflared` 代理完全运行在不同的机器上。

这是一种**高级模式**，适用于具有特定需求或复杂现有设置的用户。

### 优点
* **最大控制：** 您可以完全控制 `cloudflared` 代理，包括其版本、命令行参数和生命周期。
* **与现有设置集成：** 如果您已经有一个出于其他目的而运行的 `cloudflared` 代理，那么这是完美的选择。
* **解耦：** 将 DockFlare 的生命周期与 `cloudflared` 代理的生命周期解耦。

### 缺点
* **复杂性：** 您负责确保 `cloudflared` 代理正在运行、正确配置并连接到正确的隧道。
* **配置开销：** 您需要配置 DockFlare 才能使用此外部代理。

### 如何启用外部模式
要启用外部模式，您必须为 DockFlare 容器设置以下环境变量：

* `USE_EXTERNAL_CLOUDFLARED=true`：启用外部模式。
* `EXTERNAL_TUNNEL_ID`：必须将其设置为外部 `cloudflared` 代理配置使用的隧道的 UUID。

设置这些变量后，DockFlare 将跳过其内部代理管理，并将所有入口规则配置发送到 `EXTERNAL_TUNNEL_ID` 指定的隧道。
