# Voraussetzungen

Bevor Sie beginnen, stellen Sie sicher, dass Sie Folgendes haben:

*   **Docker & Docker Compose:** DockFlare ist eine Docker-basierte Anwendung, daher müssen sowohl Docker als auch Docker Compose auf Ihrem System installiert sein.
*   **Ein Cloudflare-Konto:** Sie benötigen ein Cloudflare-Konto, um Ihre Domains zu verwalten und API-Tokens zu erstellen.
*   **Ihre Cloudflare-Konto-ID:** Sie finden Ihre Konto-ID im Cloudflare-Dashboard.
*   **Die Zonen-ID für die Domain, die Sie verwenden möchten:** Jede Domain in Cloudflare hat eine eindeutige Zonen-ID.
*   **Ein Cloudflare API-Token:** Sie müssen ein Cloudflare API-Token mit den folgenden Berechtigungen erstellen:
    *   `Account:Cloudflare Tunnel:Edit`
    *   `Account:Account Settings:Read`
    *   `Account:Access: Apps and Policies:Edit`
    *   `Account:Access: Organizations, Identity Providers, and Groups:Edit`
    *   `Zone:Zone:Read`
    *   `Zone:DNS:Edit`

![Cloudflare API Berechtigungen](../static/images/cf.png)
