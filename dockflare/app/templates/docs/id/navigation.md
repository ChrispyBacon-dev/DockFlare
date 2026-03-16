# Selamat datang di Dokumentasi DockFlare!

DockFlare adalah ingress controller self-hosted yang kuat untuk menyederhanakan pengelolaan Cloudflare Tunnel dan Zero Trust. DockFlare memakai label Docker untuk konfigurasi otomatis sekaligus menyediakan web UI yang tangguh untuk definisi layanan manual dan override kebijakan.

Dokumentasi ini menyajikan panduan lengkap untuk DockFlare. Baik Anda pengguna baru maupun yang sudah berpengalaman, di sini Anda akan menemukan hal-hal penting yang dibutuhkan untuk memaksimalkan penggunaan DockFlare.

## Daftar Isi

*   **[Beranda](Home.md)**
*   **Memulai**
    *   [Prasyarat](Prerequisites.md)
    *   [Quick Start (Docker Compose)](Quick-Start-Docker-Compose.md)
    *   [Mengakses Web UI](Accessing-the-Web-UI.md)
*   **Konsep Inti**
    *   [Cara Kerja DockFlare](How-DockFlare-Works.md)
    *   [DockFlare Agent & Arsitektur Multi-Server](Multi-Server-Agent.md)
    *   [Praktik Terbaik Access Policy](Access-Policy-Best-Practices.md)
    *   [Zone Default Policies](Zone-Default-Policies.md)
    *   [`cloudflared` Internal vs Eksternal](Internal-vs-External-cloudflared.md)
    *   [Persistensi State](State-Persistence.md)
*   **Konfigurasi**
    *   [Label Container](Container-Labels.md)
    *   [Identity Provider](Identity-Providers.md)
    *   [Setup OAuth Provider](OAuth-Provider-Setup.md)
*   **Panduan Penggunaan**
    *   [Penggunaan Dasar (Satu Domain)](Basic-Usage-Single-Domain.md)
    *   [Menggunakan Banyak Domain (Indexed Labels)](Using-Multiple-Domains-Indexed-Labels.md)
    *   [Menggunakan Wildcard Domain](Using-Wildcard-Domains.md)
    *   [Mengelola DNS Zone](Managing-DNS-Zones.md)
    *   [Memahami Graceful Deletion](Understanding-Graceful-Deletion.md)
    *   [Menggunakan Web UI](Using-the-Web-UI.md)
    *   [Backup & Restore](Backup-and-Restore.md)
*   **Topik Lanjutan**
    *   [Mode `cloudflared` Eksternal](External-cloudflared-Mode.md)
    *   [Berpindah Antar Mode](Switching-Between-Modes.md)
    *   [Monitoring dengan Prometheus & Grafana](Monitoring-with-Prometheus-&-Grafana.md)
    *   [Tuning Performa](Performance-Tuning.md)
    *   [Content Security Policy (CSP)](Content-Security-Policy.md)
    *   [Arsitektur Keamanan & Hardening](Security-Architecture.md)
*   **Troubleshooting**
    *   [Masalah Umum](Common-Issues.md)
    *   [Debugging & Log](Debugging-&-Logs.md)
    *   [Health Check](Health-Checks.md)
    *   [Utilitas CLI](CLI-Utilities.md)
*   **[Berkontribusi](Contributing.md)**
*   **[Lisensi](License.md)**
