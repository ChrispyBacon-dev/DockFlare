# 管理 DNS 区域

DockFlare 能够管理同一 Cloudflare 帐户内多个域（Cloudflare 区域）的 DNS 记录。这允许您从同一 DockFlare 实例在 `service-a.domain-one.com` 和 `service-b.another-domain.org` 上运行服务。

## 默认区域

在 DockFlare 的初始设置过程中，您需要提供 **区域 ID**。这是 DockFlare 将创建所有 DNS 记录的 **默认区域**。如果您只打算使用单个域，那么您只需担心这一点。

## 用标签覆盖区域

要管理默认域以外的域上的服务，您可以使用 `dockflare.zonename` 标签。

此标签告诉 DockFlare 在指定的 Cloudflare 区域中为该特定服务创建 DNS 记录。

### 先决条件

为此，您必须确保您使用的 **Cloudflare API 令牌** 对您想要管理的 **所有区域** 具有 `Zone:DNS:Edit` 权限。

### 示例

假设您的默认区域是 `example.com`，但您还想在 `media.io` 上运行服务。

```yaml
services:
  # This service will be created in the default zone (example.com)
  service-one:
    image: nginx
    labels:
      - "dockflare.enable=true"
      - "dockflare.hostname=nginx.example.com"
      - "dockflare.service=http://service-one:80"

  # This service will be created in the 'media.io' zone
  service-two:
    image: portainer/portainer-ce
    labels:
      - "dockflare.enable=true"
      - "dockflare.hostname=portainer.media.io"
      - "dockflare.service=http://service-two:9000"
      # Override the default zone for this service
      - "dockflare.zonename=media.io"
```

当您部署它时，DockFlare 将：
1. 在 `example.com` 区域中为 `nginx.example.com` 创建 CNAME 记录。
2. 在 `media.io` 区域中为 `portainer.media.io` 创建 CNAME 记录。

两个主机名都将作为入口规则添加到同一 Cloudflare 隧道。

## 在 UI 中查看 DNS 记录

DockFlare Web UI 的 **设置** 页面上有一项功能，允许您查看帐户上的所有 Cloudflare 隧道以及指向它们的 DNS 记录。

为了确保 UI 可以找到所有不同区域的 DNS 记录，您可以使用 `TUNNEL_DNS_SCAN_ZONE_NAMES` 环境变量。

### `TUNNEL_DNS_SCAN_ZONE_NAMES`

此环境变量接受 UI 在查找 DNS 记录时应扫描的以逗号分隔的区域名称列表。

**示例 `docker-compose.yml`:**
```yaml
services:
  dockflare:
    image: alplat/dockflare:stable
    # ... other settings
    environment:
      # Tell the UI to scan these zones in addition to the default one
      - TUNNEL_DNS_SCAN_ZONE_NAMES=media.io,another-domain.org
```

这将确保 UI 中的 DNS 记录查看器提供指向您的隧道的所有域的完整图片。