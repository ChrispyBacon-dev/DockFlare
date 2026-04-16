# Email Prerequisites & Setup

Before enabling the Email Suite, ensure your environment and Cloudflare account are properly configured.

## Cloudflare Requirements

1.  **Domain Management:** Your domain must be active on Cloudflare.
2.  **Email Routing:** The domain must be eligible for Cloudflare Email Routing (available on most plans, including Free) and Cloudflare Email Sending (Beta Access required for outbound mail).
3.  **R2 Storage:** You must have R2 enabled in your Cloudflare dashboard. R2 includes a free tier of 10 GB, but you may need to add a payment method to your account to activate it.

## API Token Permissions

The Email Suite requires additional permissions on your existing DockFlare API Token. Update it at **User Profile > API Tokens** and add the following permissions:

| Scope | Specific Permission | Access Level | Purpose |
| :--- | :--- | :--- | :--- |
| **Account** | **Workers Scripts** | **Edit** | Deploying inbound/outbound workers |
| **Account** | **Workers KV Storage** | **Edit** | Real-time quota enforcement at the edge |
| **Account** | **R2 Storage** | **Edit** | Creating and managing transit buckets |
| **Zone** | **Email Routing** | **Edit** | Activating routing and managing rules |
| **Zone** | **DNS** | **Edit** | Creating MX, SPF, DMARC, and DKIM records |

> **Security Note:** It is highly recommended to restrict this token's "Account Resources" and "Zone Resources" to only the specific account and domains you intend to use with DockFlare.

## System Requirements

*   **DockFlare:** v3.1.0 or later.
*   **Docker:** v20.10+.
*   **Docker Compose:** v2.20+ (required for `profiles` support).
*   **Storage:** Ensure you have enough disk space on the host machine for the `mail_data` volume, which will store all email databases and attachments.
