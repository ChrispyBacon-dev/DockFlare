# 使用通配符域

DockFlare 支持使用通配符域（例如 `*.example.com`）将多个子域的流量路由到单个服务。这对于处理动态子域的应用程序特别有用，例如多租户服务或 Heimdall 等个人仪表板。

## 它是如何工作的

当您使用通配符主机名时，Cloudflare Tunnel 会将没有更具体 DNS 记录的任何子域的所有流量路由到您指定的服务。

例如，如果配置 `*.apps.example.com`，则 `service1.apps.example.com`、`service2.apps.example.com` 等的流量将全部路由到同一目标容器。

## 重要考虑因素

与常规主机名不同，DockFlare **无法自动为通配符域创建 DNS 记录**。您必须在 Cloudflare 仪表板中手动创建通配符 DNS 记录。

DockFlare 仍将管理 Cloudflare 隧道中的 **入口规则**，但初始 DNS 设置是手动步骤。

## 分步指南

以下是如何使用 DockFlare 正确设置通配符域，以 `*.plex.example.com` 为例。

### 第 1 步：手动创建通配符 DNS 记录

1. 登录您的 **Cloudflare 仪表板**。
2. 导航至您的域的 DNS 设置。
3. 单击 **添加记录** 并使用以下详细信息创建 CNAME 记录：
    * **类型：** `CNAME`
    * **名称：** `*.plex` （或者如果您的主域是 `plex.example.com`，则只是 `*`）
    * **目标：** 您隧道的公共主机名。您可以在 Cloudflare 零信任仪表板的 **访问 -> 隧道** 下找到它。它看起来像 `your-tunnel-uuid.cfargotunnel.com`。
    * **代理状态：** 确保它是 **代理**（橙色云）。

    此手动 DNS 记录告诉 Cloudflare 将 `*.plex.example.com` 的所有流量发送到您的隧道。

### 步骤 2：使用通配符标签配置您的服务

现在，使用通配符主机名标签在 `docker-compose.yml` 文件中配置您的服务。

```yaml
services:
  my-proxy-manager:
    image: nginxproxymanager/nginx-proxy-manager
    restart: unless-stopped
    networks:
      - cloudflare-net
    labels:
      - "dockflare.enable=true"
      # Use the wildcard hostname here
      - "dockflare.hostname=*.plex.example.com"
      - "dockflare.service=http://my-proxy-manager:81"
```

### 步骤 3：部署和验证

1. 保存 `docker-compose.yml` 文件并运行 `docker compose up -d`。
2. DockFlare 将检测容器并在 Cloudflare 隧道中为主机名 `*.plex.example.com` 创建入口规则。
3. 您可以在 DockFlare 网页管理界面以及 Cloudflare 仪表板中的隧道配置里验证这一点。

现在，对 `sonarr.plex.example.com` 或 `radarr.plex.example.com` 等子域的任何请求都将通过您的 Cloudflare 隧道路由到您的 `my-proxy-manager` 容器，然后该容器可以相应地处理流量。
