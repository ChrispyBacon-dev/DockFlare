# 访问网页管理界面

成功启动 DockFlare 容器后，您就可以访问网页管理界面，管理设置、查看隧道状态，并手动配置入口规则。

## 默认网址

默认情况下，DockFlare 的网页管理界面通过端口 `5000` 提供访问。请在浏览器中打开以下地址：

```
http://<your-server-ip>:5000
```

将 `<your-server-ip>` 替换为运行 DockFlare 的服务器的 IP 地址。

## 首次设置

首次访问管理界面时，系统会引导您完成 **初始设置向导**。该向导会帮助您：

1. 从现有 DockFlare 备份存档 (`dockflare_backup_*.zip`) 恢复。如果您选择此选项，系统将导入您的加密配置、状态和代理密钥，然后自动重新启动容器以应用它们。
2. 创建管理界面的管理员账户和密码。
3. 提供您的 Cloudflare 帐户 ID、区域 ID（可选）和 API 令牌。
4. 确认隧道设置并完成引导步骤。

## 登录

完成初始设置后，每次访问管理界面都会显示登录页。请使用设置过程中创建的密码登录。

## 禁用密码登录

DockFlare 提供“禁用密码登录”设置，适用于高级部署场景: DockFlare 本身已经由外部认证层（例如 Cloudflare Access）保护。**在绝大多数部署中，我们强烈不建议启用此功能**。

### 为什么存在这个设置

如果您将 DockFlare 部署在 Cloudflare Access 或其他会在到达应用前强制执行 SSO 的认证代理之后，可以禁用 DockFlare 的内置密码登录，以避免重复登录。

### 启用时存在安全风险

- ⚠️ **启用此设置后，无需身份验证即可访问所有 API 端点**
- ⚠️ **Docker 网络暴露：** 即使 DockFlare 在公网侧已由 Cloudflare Access 保护，同一 Docker 网络中的容器仍然可以绕过外部身份验证并直接访问 DockFlare API
- ⚠️ **应用自身不再强制认证：** DockFlare 会假定外部认证层已经覆盖了所有访问路径

### 攻击向量示例

```
Internet → Cloudflare Access (Protected) → DockFlare ✅
         ↓
Docker Network → Other Container → DockFlare API (Unprotected) ❌
```

即使 DockFlare 受到来自互联网的 Cloudflare Access 的保护，在同一 Docker 网络上运行的任何容器都可以绕过该保护并直接访问 DockFlare 的 API 端点，而无需进行身份验证。

### 推荐方法

不要禁用密码身份验证，而是使用以下安全选项之一：

1. **本地 DockFlare 凭据** - DockFlare 内置的简单密码身份验证
2. **OAuth/OIDC 提供程序** - 配置 Google、GitHub、Azure AD 等身份提供商，以便在不牺牲安全性的前提下实现便捷的单点登录（参见 [OAuth 提供程序设置](OAuth-Provider-Setup.md)）

这两个选项都提供正确的身份验证，同时保持 SSO 的便利性。OAuth 选项为您提供单点登录体验，而不会带来禁用身份验证的安全风险。

### 结论

除非您有一个非常具体、易于理解的网络隔离安全架构，否则请保持密码登录启用状态并使用 OAuth 以方便起见。
