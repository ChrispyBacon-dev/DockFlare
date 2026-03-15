# 身份提供商

> **📌 重要提示：** 本指南用于配置 **Cloudflare 访问策略中的身份提供商**，以保护您的服务和应用程序。如果您想为 **DockFlare 网页管理界面登录** 配置 OAuth/OIDC，请参阅 [OAuth 提供程序设置](OAuth-Provider-Setup.md)。

身份提供商（IdP）可为受 Cloudflare Zero Trust 保护的应用启用 OAuth/OIDC 身份验证。DockFlare 让您能够更轻松地管理 IdP，并将其集成到访问策略中。

## 概述

您无需只依赖基于电子邮件的身份验证，也可以使用 Google、GitHub、Azure AD 等常见 OAuth 提供程序。用户使用现有账号完成身份验证，从而获得流畅且安全的登录体验。

## 支持的提供程序

DockFlare 支持以下身份提供商：

- **Google** - 个人 Google 账号
- **Google Workspace** - 可选域限制的 Google Workspace（G Suite）账号
- **Microsoft Azure AD** - Microsoft Entra ID（Azure Active Directory）
- **Okta** - Okta Identity Cloud
- **GitHub** - GitHub OAuth
- **通用 OpenID Connect** - 任何兼容 OIDC 的提供程序

## 管理身份提供商

### 添加身份提供商

1. 进入 **访问策略** 页面。
2. 在 **身份提供商** 部分中，点击 **添加提供商**。
3. 填写必填字段：
   - **友好名称**：DockFlare 内部使用的名称，例如 `google-main` 或 `github-dev`
   - **显示名称**：在 Cloudflare 仪表板中显示的名称
   - **提供程序类型**：选择您的 OAuth 提供程序
   - **配置**：提供程序专属凭据，请参考下方的设置指南
4. 点击 **创建提供商**。
5. 使用提供的测试 URL 测试该提供程序。

### 从 Cloudflare 同步

如果您已经在 Cloudflare Zero Trust 中配置了 IdP：

1. 在身份提供商部分点击 **从 Cloudflare 同步**。
2. DockFlare 会导入所有现有 IdP，并自动生成友好名称。
3. 您可以重命名这些友好名称，以便在标签中更容易引用。

### 测试身份提供商

创建 IdP 后，您可以对其进行测试：

1. 点击提供商旁边的 **⋮** 菜单。
2. 选择 **测试 IdP**。
3. 会打开一个新窗口，您可以在其中进行身份验证。
4. 确认登录流程是否正常工作。

## 提供程序设置指南

### Google（个人账号）

**步骤 1：创建 OAuth 凭据**

1. 前往 [Google Cloud Console](https://console.cloud.google.com/)。
2. 创建一个新项目或选择现有项目。
3. 进入 **API 和服务** → **凭据**。
4. 点击 **创建凭据** → **OAuth 客户端 ID**。
5. 选择 **Web 应用程序**。
6. 添加授权重定向 URI：
   ```
   https://<your-team>.cloudflareaccess.com/cdn-cgi/access/callback
   ```
   <small>您可以在 <a href="https://one.dash.cloudflare.com/{{ACCOUNT_ID}}/settings/custom_pages" target="_blank">Zero Trust</a> 的 设置 > 自定义页面 中找到团队名称。</small>
7. 复制 **客户端 ID** 和 **客户端密钥**。

**步骤 2：在 DockFlare 中配置**

- **客户端 ID**：粘贴 Google Cloud Console 中的值
- **客户端密钥**：粘贴 Google Cloud Console 中的值

---

### Google Workspace

与上面的 Google 配置相同，但多了一个可选字段：

- **Apps Domain**：（可选）限制为特定域名，例如 `example.com`

如果设置了该字段，则只有 `@example.com` 邮箱地址的用户才能通过身份验证。

---

### Microsoft Azure AD

**步骤 1：在 Azure 中注册应用**

1. 前往 [Azure 门户](https://portal.azure.com/)。
2. 进入 **Azure Active Directory** → **应用注册**。
3. 点击 **新建注册**。
4. 为应用命名，例如 `DockFlare Access`。
5. 在 **重定向 URI** 中选择 **Web**，然后输入：
   ```
   https://<your-team>.cloudflareaccess.com/cdn-cgi/access/callback
   ```
   <small>您可以在 <a href="https://one.dash.cloudflare.com/{{ACCOUNT_ID}}/settings/custom_pages" target="_blank">Zero Trust</a> 的 设置 > 自定义页面 中找到团队名称。</small>
6. 点击 **注册**。
7. 复制 **应用程序（客户端）ID**。
8. 复制 **目录（租户）ID**。
9. 前往 **证书和密码** → **新建客户端密码**。
10. 创建一个密码并复制其 **值**。

**步骤 2：在 DockFlare 中配置**

- **应用程序（客户端）ID**：粘贴 Azure 中的值
- **目录（租户）ID**：粘贴 Azure 中的值
- **客户端密钥**：粘贴 Azure 中的值

---

### GitHub

**步骤 1：创建 OAuth 应用**

1. 前往 [GitHub 开发者设置](https://github.com/settings/developers)。
2. 点击 **New OAuth App**。
3. 填写以下内容：
   - **Application name**：DockFlare Access
   - **Homepage URL**：`https://your-domain.com`
   - **Authorization callback URL**：
     ```
     https://<your-team>.cloudflareaccess.com/cdn-cgi/access/callback
     ```
     <small>您可以在 <a href="https://one.dash.cloudflare.com/{{ACCOUNT_ID}}/settings/custom_pages" target="_blank">Zero Trust</a> 的 设置 > 自定义页面 中找到团队名称。</small>
4. 点击 **Register application**。
5. 复制 **客户端 ID**。
6. 点击 **Generate a new client secret** 并复制它。

**步骤 2：在 DockFlare 中配置**

- **客户端 ID**：粘贴 GitHub 中的值
- **客户端密钥**：粘贴 GitHub 中的值

---

### Okta

**步骤 1：在 Okta 中创建应用**

1. 登录您的 [Okta 管理控制台](https://admin.okta.com/)。
2. 进入 **Applications** → **Create App Integration**。
3. 选择 **OIDC - OpenID Connect**。
4. 选择 **Web Application**。
5. 配置：
   - **登录重定向 URI**：
     ```
     https://<your-team>.cloudflareaccess.com/cdn-cgi/access/callback
     ```
     <small>您可以在 <a href="https://one.dash.cloudflare.com/{{ACCOUNT_ID}}/settings/custom_pages" target="_blank">Zero Trust</a> 的 设置 > 自定义页面 中找到团队名称。</small>
6. 点击 **Save**。
7. 复制 **客户端 ID** 和 **客户端密钥**。
8. 记下您的 **Okta 域名**，例如 `https://dev-12345.okta.com`。

**步骤 2：在 DockFlare 中配置**

- **Okta 账户 URL**：您的 Okta 域名，例如 `https://dev-12345.okta.com`
- **客户端 ID**：粘贴 Okta 中的值
- **客户端密钥**：粘贴 Okta 中的值

---

### 通用 OpenID Connect

对于任何兼容 OIDC 的提供程序：

**步骤 1：获取提供程序配置**

从 IdP 文档中获取以下信息：
- 授权 URL
- Token URL
- JWKS URL（JSON Web Key Set）
- 客户端 ID
- 客户端密钥

**步骤 2：在 DockFlare 中配置**

- **授权 URL**：提供程序的 OAuth 授权端点
- **Token URL**：提供程序的令牌端点
- **JWKS URL**：提供程序的 JWKS 端点，用于签名校验
- **客户端 ID**：来自您的提供程序
- **客户端密钥**：来自您的提供程序

---

## 在访问策略中使用身份提供商

### 在访问组中

1. 进入 **访问策略** → **高级访问策略**。
2. 点击 **创建新组**，或编辑现有组。
3. 在 **策略规则** 部分中：
   - **身份提供商**：选择一个或多个 IdP
   - **允许的电子邮件或域**：**使用 IdP 时必填**。请指定允许的电子邮件地址。
4. 保存该组。

### 身份验证模式

您有两个选项：

1. **仅电子邮件**：输入电子邮件地址，不选择任何 IdP。用户通过一次性 PIN 完成身份验证。
2. **IdP + 电子邮件（必填）**：选择 IdP 并输入允许的电子邮件。用户必须通过所选 IdP 完成身份验证，并且电子邮件必须位于允许列表中。

**⚠️ 安全提示：** 使用身份提供商时，您**必须**指定允许的电子邮件地址。这可以防止未授权访问。例如，如果没有电子邮件限制，选择 `Google` 作为 IdP 将允许任何拥有 Google 账号的人访问您的服务。

### 在 Docker 标签中

在容器标签中使用友好名称：

```yaml
services:
  myapp:
    image: myapp:latest
    labels:
      dockflare.enable: "true"
      dockflare.hostname: "app.example.com"
      dockflare.access.group: "my-access-group"
```

访问组 `my-access-group` 会自动将 IdP 的友好名称解析为 Cloudflare UUID。

---

## 最佳实践

### 命名约定

使用清晰且有描述性的名称：
- ✅ `google-main`、`github-dev`、`azure-work`
- ❌ `idp1`、`test`、`new`

### 安全

- **定期轮换密钥**：定期更新客户端密钥
- **限制范围**：对于 Google Workspace 和 Azure AD，尽可能限制到特定域
- **在生产前测试**：在应用到生产服务之前务必先测试 IdP
- **监控使用情况**：检查 Cloudflare 日志，发现未授权访问尝试

### 多环境

为不同环境创建独立的 IdP：
- `google-dev` - 开发环境
- `google-staging` - 预发布环境
- `google-prod` - 生产环境

### 使用 IdP 时的电子邮件要求

**重要：** 出于安全考虑，IdP 身份验证始终需要电子邮件限制。

**访问组示例：**
- **身份提供商**：`google-main`
- **允许的电子邮件**：`admin@example.com, user@example.com, @contractor-domain.com`

该配置允许以下用户访问：
- 通过 `google-main` IdP（Google OAuth）完成身份验证 **且**
- 电子邮件地址匹配 `admin@example.com`、`user@example.com` 或任意 `@contractor-domain.com` 地址

**工作方式如下：**
1. 用户在受保护的应用上点击登录。
2. 用户被重定向到 Google OAuth 登录页面。
3. Google 完成身份验证后，Cloudflare 会检查该电子邮件是否在允许列表中。
4. 只有匹配允许列表时才会授予访问权限。

---

## 故障排除

### “无效的重定向 URI”错误

**原因**：OAuth 提供程序中的重定向 URI 与 Cloudflare 期望的 URI 不一致。

**解决方案**：请确保您添加的是以下准确 URI：
```
https://<your-team>.cloudflareaccess.com/cdn-cgi/access/callback
```
<small>您可以在 <a href="https://one.dash.cloudflare.com/{{ACCOUNT_ID}}/settings/custom_pages" target="_blank">Zero Trust</a> 的 设置 > 自定义页面 中找到团队名称。</small>

请将 `<your-team>` 替换为您的 Cloudflare Zero Trust 团队名称。

---

### “IdP 测试失败”

**原因**：凭据错误或配置不正确。

**解决方案**：
1. 确认客户端 ID 和客户端密钥是否正确。
2. 检查您的提供程序中是否已启用 OAuth 应用。
3. 对于 Azure AD，请同时确认客户端 ID 和租户 ID。
4. 使用 Cloudflare 提供的测试 URL 测试该提供程序。

---

### “无法删除由系统管理的 IdP”

**原因**：尝试删除内置的 One-Time PIN 提供程序。

**解决方案**：`onetimepin` 提供程序由系统管理，无法删除。基于电子邮件的 OTP 身份验证需要它。

---

### “在 Docker 标签中找不到 IdP”

**原因**：在标签中使用了 Cloudflare UUID，而不是友好名称。

**解决方案**：请在访问组配置中使用友好名称，例如 `google-main`，而不是 UUID。

---

## 相关文档

- [访问策略最佳实践](Access-Policy-Best-Practices.md)
- [区域默认策略](Zone-Default-Policies.md)
- [容器标签](Container-Labels.md)
- [安全架构](Security-Architecture.md)

---
