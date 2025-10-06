# Prerequisites  

Before you begin, ensure you have the following:  

*   **Docker & Docker Compose:** DockFlare is a Docker-based application, so you'll need both Docker and Docker Compose installed on your system.
*   **A Cloudflare Account:** You'll need a Cloudflare account to manage your domains and create API tokens.
*   **Your Cloudflare Account ID:** You can find your Account ID in the Cloudflare dashboard.
*   **The Zone ID for the domain you wish to use:** Each domain in Cloudflare has a unique Zone ID.
*   **A Cloudflare API Token:** You'll need to create a Cloudflare API token with the following permissions:
    *   `Account:Cloudflare Tunnel:Edit`
    *   `Account:Account Settings:Read`
    *   `Account:Access: Apps and Policies:Edit`
    *   `Account:Access: Organizations, Identity Providers, and Groups:Edit`
    *   `Zone:Zone:Read`
    *   `Zone:DNS:Edit`  

![Cloudflare API Permissions](../static/images/cf.png)
