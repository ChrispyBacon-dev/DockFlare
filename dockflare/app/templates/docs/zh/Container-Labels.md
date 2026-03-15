# 容器标签参考

DockFlare 主要通过附加到容器的 Docker 标签进行配置。此页面提供所有支持的标签的综合参考。

## 基本配置

这些标签控制容器的基本路由和服务定义。

|标签|描述 |示例|
| :--- | :--- | :--- |
| `dockflare.enable` | **必需。** 主开关。必须设置为 `true` 以便 DockFlare 管理容器。 | `dockflare.enable=true` |
| `dockflare.hostname` | **必需。** 您的服务的面向公众的主机名。 | `dockflare.hostname=myservice.example.com` |
| `dockflare.service` | **必需。** Cloudflare Tunnel 应连接到的服务的内部 URL。可以是 `http`、`https`、`tcp`、`ssh`、`rdp`、`http_status:XXX` 或 `bastion`。 | `dockflare.service=http://my-app-container:8080` |
| `dockflare.path` |路由到此服务的 URL 路径。对于在同一主机名上公开多个服务很有用。 | `dockflare.path=/api` |
| `dockflare.zonename` | （可选）应在其中创建 DNS 记录的显式 Cloudflare 区域（域）。如果省略，DockFlare 现在会根据主机名自动检测区域，并且仅在自动检测失败时才回退到配置的默认值 (`CF_ZONE_ID`)。 | `dockflare.zonename=another-domain.com` |
| `dockflare.no_tls_verify` |如果设置为 `true`，则禁用 `cloudflared` 与源服务之间的连接的 TLS 证书验证。对于具有自签名证书的来源很有用。 | `dockflare.no_tls_verify=true` |
| `dockflare.originsrvname` |为与源的 TLS 连接设置特定的服务器名称指示 (SNI) 主机名。这在 Cloudflare 仪表板中也称为“源服务器名称”。 | `dockflare.originsrvname=internal.service.local` |
| `dockflare.httpHostHeader` |覆盖从 `cloudflared` 发送到源服务的 `Host` 标头。 | `dockflare.httpHostHeader=custom-host.internal` |
| `dockflare.http2_origin` |如果设置为 `true`，则为 `cloudflared` 和源服务之间的连接启用 HTTP/2 协议。 gRPC 服务所需。仅适用于 HTTP/HTTPS 服务。 | `dockflare.http2_origin=true` |
| `dockflare.disable_chunked_encoding` |如果设置为 `true`，则禁用通过 HTTP/1.1 的分块传输编码。对于 WSGI 服务器（Flask、Django、FastAPI）和其他不能正确支持分块请求的源很有用。仅适用于 HTTP/HTTPS 服务。 | `dockflare.disable_chunked_encoding=true` |

> **提示：** 从 DockFlare v3.0 开始，对于大多数工作负载，您都可以省略 `dockflare.zonename`。主控端会通过匹配主机名后缀自动检测正确的 Cloudflare 区域，只有在找不到匹配项时才会回退到配置的默认区域。仅当您需要显式将记录创建到其他区域时，再提供该标签。

> **注意：** Cloudflare 的 **将 SNI 与主机匹配** 选项可在仪表板中的 DockFlare 手动规则配置中使用。目前它不是通过 Docker 标签设置的。

---

## 访问策略配置

这些标签允许您动态创建和管理 Cloudflare Access 应用程序以保护您的服务。

**注意：** 强烈建议使用**访问组** (`dockflare.access.group`) 来管理策略。DockFlare 3.0.3 会将每个访问组同步为 Cloudflare 可复用访问策略，便于一处维护、多处复用，并支持双向编辑。单独的 `dockflare.access.*` 标签更适合一次性、特殊的配置需求。如果使用 `dockflare.access.group` 或 `dockflare.access.groups`，则其他 `dockflare.access.*` 标签会被忽略。

### v3.0.3 中的重要变化

#### 系统默认绕过策略

从 v3.0.3 开始，当您使用 `dockflare.access.policy=bypass` 或 `dockflare.access.group=bypass` 时，您的服务将引用系统管理的 `public-default-bypass` 可重用策略，而不是创建内联策略。这可以让您的 Cloudflare 仪表板保持干净。

- **v3.0.3 之前：** 每个绕过规则创建一个单独的内联策略
- **v3.0.3+：** 所有绕过规则共享一个规范的 `public-default-bypass` 策略

#### 旧标签迁移

DockFlare 自动迁移旧版绕过标签以使用集中式系统策略：

- `dockflare.access.policy=bypass` → 使用 `public-default-bypass` 系统策略
- `dockflare.access.group=bypass` → 使用 `public-default-bypass` 系统策略

迁移在容器处理和协调期间透明地进行。您的容器将继续工作，无需任何更改。

#### 简化的访问配置

对于复杂的访问场景（邮箱/域名认证、IP白名单等），现在建议：

1. 在**访问策略**页面创建访问组
2. 用 `dockflare.access.group=your-group-id` 引用它

快速创建选项已从管理界面中移除，以鼓励采用这种最佳实践工作流程。

#### 区域默认策略标签

`dockflare.access.policy=default_tld` 标签仍然有效，并将继承您区域的 `*.domain.com` 通配符策略的保护。如果不存在区域策略，则该服务将是公共的（无访问应用程序）。

**建议：** 在管理界面中为所有域创建区域默认策略，以提高安全性。

|标签|描述 |示例|
| :--- | :--- | :--- |
| `dockflare.access.group` | 应用于此服务的单个预配置访问组 ID。该 ID 可以在 DockFlare 管理界面的“访问策略”页面中找到。 | `dockflare.access.group=internal-tools-policy` |
| `dockflare.access.groups` |要应用的访问组 ID 的逗号分隔列表。这允许您将多个策略分层到单个服务上。 | `dockflare.access.groups=allow-team-a,allow-admins` |
| `dockflare.access.policy` |主要策略类型。可以是 `bypass` （公共）、`authenticate` （需要登录）或 `default_tld` （继承自 `*.domain.com` 策略）。如果未设置，该服务将是公开的。优先选择访问组以实现可重用的策略；这些标签用于专门的覆盖。 | `dockflare.access.policy=authenticate` |
| `dockflare.access.name` | Cloudflare Access 应用程序的自定义名称。默认为 `DockFlare-{hostname}`。 | `dockflare.access.name=My Web App Access` |
| `dockflare.access.session_duration` |经过身份验证的用户的会话持续时间（例如，`24h`、`30m`）。默认为 `24h`。 | `dockflare.access.session_duration=1h` |
| `dockflare.access.app_launcher_visible` |如果 `true`，则使应用程序在 Cloudflare Access 应用程序启动器中可见。 | `dockflare.access.app_launcher_visible=true` |
| `dockflare.access.allowed_idps` |允许的身份提供商 (IdP) UUID 的逗号分隔列表。您可以在 Cloudflare 零信任仪表板中找到这些内容。 | `dockflare.access.allowed_idps=uuid1,uuid2` |
| `dockflare.access.auto_redirect_to_identity` |如果 `true`，用户将立即重定向到 IdP 登录页面，而不是 Cloudflare Access 启动页面。 | `dockflare.access.auto_redirect_to_identity=true` |
| `dockflare.access.custom_rules` |表示 Cloudflare 访问策略规则数组的 JSON 字符串。这为复杂的一次性策略提供了最大的灵活性。 | `dockflare.access.custom_rules='[{"email":{"email":"user@example.com"},"action":"allow"}]'` |

---

## 多个域的索引标签

DockFlare 支持使用索引标签为单个容器定义多个主机名。这对于在不同的公共主机名上公开同一服务的不同端口或路径非常有用。

要使用索引标签，请在标签前添加一个从 `0` 开始的整数前缀。

* 始终需要索引主机名 (`<index>.hostname`)。
* 同一索引处的其他标签（例如 `<index>.service`、`<index>.path`）将覆盖该特定主机名的基本（非索引）标签。
* 如果未提供索引标签，它将回退到相应基本标签的值。

### 示例

此示例公开来自单个容器的两个主机名：
1. `app.example.com` 路由到端口 `80` 上的主 Web 界面。
2. `api.example.com` 路由到端口 `3000` 上的 API，并通过特定访问组进行保护。

```yaml
services:
  my-multi-service:
    image: my-app
    labels:
      - "dockflare.enable=true"

      # --- Definition 0 ---
      - "dockflare.0.hostname=app.example.com"
      - "dockflare.0.service=http://my-multi-service:80"

      # --- Definition 1 ---
      - "dockflare.1.hostname=api.example.com"
      - "dockflare.1.service=http://my-multi-service:3000"
      - "dockflare.1.access.group=api-access-policy"
```
