# Email Prerequisites & Setup

Before enabling the Email Suite, ensure your environment and Cloudflare account are properly configured.

## Cloudflare Requirements

1.  **Domain Management:** Your domain must be active on Cloudflare.
2.  **Email Routing (Inbound):** Cloudflare Email Routing is available on all plans, including Free. DockFlare configures the required MX, SPF, and DMARC records automatically.
3.  **Email Sending (Outbound):** Cloudflare Email Sending is currently in Beta. DockFlare automatically configures the DKIM signing records and sending subdomain. However, sending to external addresses requires:
    - A **Cloudflare Workers Paid Plan** ($5/month).
    - Manual activation of **CF Email Sending (Beta)** in the Cloudflare Dashboard under **Email → Email Sending**.
    - Without these steps, outbound mail is restricted to verified Cloudflare addresses only.
4.  **R2 Storage:** You must have R2 enabled in your Cloudflare dashboard. R2 includes a free tier of 10 GB, but you may need to add a payment method to your account to activate it.

## API Token Permissions

The Email Suite requires additional permissions on your existing DockFlare API Token. Update it at **User Profile > API Tokens** and add the following permissions:

| Scope | Specific Permission | Access Level | Purpose |
| :--- | :--- | :--- | :--- |
| **Account** | **Workers Scripts** | **Edit** | Deploying inbound/outbound workers |
| **Account** | **Workers KV Storage** | **Edit** | Real-time quota enforcement at the edge |
| **Account** | **R2 Storage** | **Edit** | Creating and managing transit buckets |
| **Account** | **Access: Apps and Policies** | **Edit** | Create a bypass for the inbound email webhook path when Webmail is protected by Cloudflare Access |
| **Zone** | **Email Routing** | **Edit** | Activating routing and managing rules |
| **Zone** | **DNS** | **Edit** | Creating MX, SPF, DMARC, and DKIM records |

> **Security Note:** It is highly recommended to restrict this token's "Account Resources" and "Zone Resources" to only the specific account and domains you intend to use with DockFlare.

## System Requirements

*   **DockFlare:** v3.1.0 or later.
*   **Docker:** v20.10+.
*   **Docker Compose:** v2.20+ (required for `profiles` support).
*   **Storage:** Ensure you have enough disk space on the host machine for the `mail_data` volume, which will store all email databases and attachments.
