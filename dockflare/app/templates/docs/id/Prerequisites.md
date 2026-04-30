# Prasyarat

Sebelum mulai, pastikan Anda sudah menyiapkan hal-hal berikut:

*   **Docker & Docker Compose:** DockFlare adalah aplikasi berbasis Docker, jadi Anda memerlukan Docker dan Docker Compose terpasang di sistem Anda.
*   **Akun Cloudflare:** Anda memerlukan akun Cloudflare untuk mengelola domain dan membuat API token.
*   **Cloudflare Account ID Anda:** Account ID dapat ditemukan di dashboard Cloudflare.
*   **Zone ID untuk domain yang ingin digunakan:** Setiap domain di Cloudflare memiliki Zone ID yang unik.
*   **Cloudflare API Token:** Buat API token Cloudflare dengan permission berikut:
    * `Account:Cloudflare Tunnel:Write`
    * `Account:Account Settings:Read`
    * `Account:Access: Apps and Policies:Write`
    * `Account:Access: Organizations, Identity Providers, and Groups:Write`
    * `Account:Access: Service Tokens:Write`
    * `Zone:Zone:Read`
    * `Zone:DNS:Write`

    **For optional DockFlare Email features, add these additional permissions:**
    * `Workers Scripts:Write`
    * `Workers KV Storage:Write`
    * `Workers R2 Storage:Write`
    * `Email Routing Addresses:Write`
    * `Email Routing Rules:Write`

![Cloudflare API Permissions](../static/images/cf.png)
