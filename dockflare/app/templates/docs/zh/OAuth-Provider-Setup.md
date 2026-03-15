## OAuth 提供程序设置

> **📌 重要提示：** 本指南用于配置 **DockFlare 网页管理界面的身份验证**（即登录 DockFlare 本身）。如果您想为 **Cloudflare 访问策略** 配置 OAuth/OIDC 以保护您的服务，请参阅 [身份提供商](Identity-Providers.md)。

DockFlare 支持通过 OpenID Connect（OIDC）将用户身份验证委托给外部身份提供商。这样可以为 DockFlare 网页管理界面启用单点登录（SSO），并与 Google、Authentik、Okta 等 IdP 集成。

### 添加新的提供程序

请按照以下步骤添加新的 OIDC 提供程序：

1. **进入设置：** 在主仪表板中打开 **设置** 页面。
2. **找到 OAuth 区域：** 向下滚动到 **OAuth 身份验证** 部分。
3. **添加提供程序：** 点击 **添加提供程序** 按钮，打开配置表单。

您将看到以下字段：

* **提供程序类型：** 固定为 `OpenID Connect (OIDC)`，这是现代联合身份验证的标准。
* **发行者 URL：** 这是最关键的字段。它是 OIDC 提供程序的基础 URL，DockFlare 会使用它自动发现提供程序配置。例如，`https://accounts.google.com` 或 `https://authentik.yourdomain.com/application/o/dockflare/`。
* **提供程序 ID：** 该提供程序的简短、唯一且全小写的名称（例如 `google`、`authentik-corp`）。这个 ID 会在内部以及回调 URL 中使用。
* **显示名称：** 显示在登录按钮上的名称（例如 `Google`、`Corporate SSO`）。
* **客户端 ID：** DockFlare 应用的公开标识符，可从 OIDC 提供程序的开发者控制台获取。
* **客户端密钥：** DockFlare 应用的机密密钥，同样来自 OIDC 提供程序的控制台。
* **启用提供程序：** 该复选框允许你随时启用或禁用此提供程序。

填写完成后，点击 **添加提供程序** 保存配置。

### 查找您的回调 URL

添加提供程序后，所需的**回调 URL**（也称为“授权重定向 URI”）会显示在设置页面中该提供程序的条目下方。

你必须完整复制这个 URL，并将其加入提供程序管理控制台中的允许回调 URL 列表。

---

### 示例：配置 Google

下面是将 Google 配置为 OAuth 提供程序的快速示例。

1. **进入 Google Cloud Console：** 打开 [API 和服务 > 凭据](https://console.cloud.google.com/apis/credentials) 页面。
2. **创建凭证：** 单击 **+ CREATE CREDENTIALS** 并选择 **OAuth 客户端 ID**。
3. **配置应用：**
    * 将 **应用程序类型** 设置为 **Web 应用程序**。
    * 为应用命名，例如 “DockFlare”。
4. **添加重定向 URI：**
    * 在 **授权重定向 URI** 下，单击 **+ 添加 URI**。
    * 输入 DockFlare 提供的回调 URL，格式类似 `https://your-dockflare-domain.com/auth/google/callback`。
5. **创建并复制：** 点击 **创建**。系统会显示包含 **客户端 ID** 和 **客户端密钥** 的窗口。复制这两个值。
6. **在 DockFlare 中填写：**
    * **发行人网址：** `https://accounts.google.com`
    * **提供程序 ID：** `google`
    * **显示名称：** `Google`
    * **客户端 ID：** `(Your Client ID from Google)`
    * **客户端密钥：** `(Your Client Secret from Google)`

在 DockFlare 中保存该提供程序后，你就可以使用 Google 账户登录。

---

### 使用 OAuth 和访问策略配置 DockFlare

在使用 OAuth 身份验证时，您通常会希望用访问策略保护 DockFlare 主界面，同时确保 OAuth 回调路径能够正常工作。如果您的 DockFlare 实例配置了 IP 限制或其他访问控制，这一点尤其重要。

#### **最佳实践：为 OAuth 回调设置 bypass 策略**

使用带索引的标签，为主界面和 OAuth 回调路径分别创建独立规则：

```yaml
services:
  dockflare:
    image: alplat/dockflare:stable
    labels:
      # Main DockFlare interface with access policy
      - "dockflare.enable=true"
      - "dockflare.hostname=dockflare.example.com"
      - "dockflare.service=http://dockflare:5000"
      - "dockflare.access.group=team"  # your custom access policy

      # OAuth callback paths with bypass policy (required for OAuth to work)
      - "dockflare.0.hostname=dockflare.example.com"
      - "dockflare.0.path=/auth/google/callback"
      - "dockflare.0.service=http://dockflare:5000"
      - "dockflare.0.access.policy=bypass"

      # Add additional callback paths for other providers if needed
      - "dockflare.1.hostname=dockflare.example.com"
      - "dockflare.1.path=/auth/github/callback"
      - "dockflare.1.service=http://dockflare:5000"
      - "dockflare.1.access.policy=bypass"
```

#### **为什么需要这样配置**

- **保护主界面**：你的 DockFlare 仪表板仍然受所选访问策略保护
- **保证 OAuth 可用**：OAuth 回调请求可以顺利到达 DockFlare，而不会被身份验证阻挡
- **更安全**：只绕过指定的回调路径，而不是整个应用
- **更灵活**：可与各种访问策略组合使用，例如基于 IP 或基于身份验证的策略

#### **重要说明**

1. **路径必须精确匹配**：回调路径必须与 OAuth 提供程序配置中期望的路径完全一致。
2. **多个提供程序**：为每个已配置的 OAuth 提供程序分别添加一条独立的索引规则。
3. **不要使用通配符**：出于安全考虑，应避免使用通配符路径，而应明确指定回调 URL。
4. **完成后测试**：配置完成后，同时测试主界面的受保护访问和 OAuth 登录流程。
