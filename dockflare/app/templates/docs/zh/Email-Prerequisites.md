# 邮件套件前提条件与配置

在启用邮件套件之前，请确保您的环境和 Cloudflare 账户已正确配置。

## Cloudflare 要求

1.  **域名管理：** 您的域名必须在 Cloudflare 上处于活动状态。
2.  **邮件路由（收件）：** Cloudflare Email Routing 在所有套餐均可使用，包括免费套餐。DockFlare 会自动配置所需的 MX、SPF 和 DMARC 记录。
3.  **邮件发送（发件）：** Cloudflare Email Sending 目前处于 Beta 阶段。DockFlare 会自动配置 DKIM 签名记录和发送子域名。但是，向外部地址发送邮件需要：
    - **Cloudflare Workers 付费套餐**（每月 5 美元）。
    - 在 Cloudflare 控制台的 **Email → Email Sending** 下手动激活 **CF Email Sending（Beta）**。
    - 未完成以上步骤时，外发邮件仅限于发送至已在 Cloudflare 账户中验证的地址。
4.  **R2 存储：** 必须在 Cloudflare 控制台中启用 R2。R2 包含 10 GB 免费额度，但可能需要添加付款方式才能激活。

## API 令牌权限

邮件套件需要在现有的 DockFlare API 令牌上添加额外权限。请在 **用户档案 > API 令牌** 中进行更新，添加以下权限：

| 作用域 | 具体权限 | 访问级别 | 用途 |
| :--- | :--- | :--- | :--- |
| **账户** | **Workers Scripts** | **编辑** | 部署入站/出站 Worker |
| **账户** | **Workers KV Storage** | **编辑** | 在边缘实时执行配额策略 |
| **账户** | **R2 Storage** | **编辑** | 创建和管理中转存储桶 |
| **账户** | **Access: Apps and Policies** | **编辑** | 当 Webmail 受 Cloudflare Access 保护时，为入站邮件 Webhook 路径创建绕过策略 |
| **区域** | **Email Routing** | **编辑** | 启用路由并管理规则 |
| **区域** | **DNS** | **编辑** | 创建 MX、SPF、DMARC 和 DKIM 记录 |

> **安全提示：** 强烈建议将此令牌的「账户资源」和「区域资源」限定为仅用于 DockFlare 的特定账户和域名。

## 系统要求

*   **DockFlare：** v3.1.0 或更高版本。
*   **Docker：** v20.10+。
*   **Docker Compose：** v2.20+（`profiles` 支持所需）。
*   **存储空间：** 确保主机上有足够的磁盘空间用于 `mail_data` 卷，该卷将存储所有邮件数据库和附件。
