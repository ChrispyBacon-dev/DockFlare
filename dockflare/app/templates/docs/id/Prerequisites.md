# Prasyarat

Sebelum mulai, pastikan Anda sudah menyiapkan hal-hal berikut:

*   **Docker & Docker Compose:** DockFlare adalah aplikasi berbasis Docker, jadi Anda memerlukan Docker dan Docker Compose terpasang di sistem Anda.
*   **Akun Cloudflare:** Anda memerlukan akun Cloudflare untuk mengelola domain dan membuat API token.
*   **Cloudflare Account ID Anda:** Account ID dapat ditemukan di dashboard Cloudflare.
*   **Zone ID untuk domain yang ingin digunakan:** Setiap domain di Cloudflare memiliki Zone ID yang unik.
*   **Cloudflare API Token:** Buat API token Cloudflare dengan permission berikut:
    *   `Account:Cloudflare Tunnel:Edit`
    *   `Account:Account Settings:Read`
    *   `Account:Access: Apps and Policies:Edit`
    *   `Account:Access: Organizations, Identity Providers, and Groups:Edit`
    *   `Zone:Zone:Read`
    *   `Zone:DNS:Edit`

![Cloudflare API Permissions](../static/images/cf.png)
