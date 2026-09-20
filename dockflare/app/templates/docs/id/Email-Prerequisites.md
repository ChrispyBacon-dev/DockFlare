# Prasyarat & Konfigurasi Email

Sebelum mengaktifkan Email Suite, pastikan lingkungan dan akun Cloudflare Anda sudah dikonfigurasi dengan benar.

## Persyaratan Cloudflare

1.  **Manajemen Domain:** Domain Anda harus aktif di Cloudflare.
2.  **Email Routing (Masuk):** Cloudflare Email Routing tersedia di semua paket, termasuk paket Gratis. DockFlare secara otomatis mengonfigurasi record MX, SPF, dan DMARC yang diperlukan.
3.  **Email Sending (Keluar):** Cloudflare Email Sending saat ini dalam tahap Beta. DockFlare secara otomatis mengonfigurasi record penandatanganan DKIM dan subdomain pengiriman. Namun, pengiriman ke alamat eksternal memerlukan:
    - **Cloudflare Workers Paid Plan** ($5/bulan).
    - Aktivasi manual **CF Email Sending (Beta)** di Dashboard Cloudflare di bawah **Email → Email Sending**.
    - Tanpa langkah-langkah ini, email keluar dibatasi hanya untuk alamat Cloudflare yang telah diverifikasi.
4.  **Penyimpanan R2:** R2 harus diaktifkan di dashboard Cloudflare Anda. R2 mencakup tier gratis 10 GB, tetapi Anda mungkin perlu menambahkan metode pembayaran untuk mengaktifkannya.

## Izin Token API

Email Suite memerlukan izin tambahan pada Token API DockFlare Anda yang ada. Perbarui di **Profil Pengguna > Token API** dan tambahkan izin berikut:

| Cakupan | Izin Spesifik | Level Akses | Tujuan |
| :--- | :--- | :--- | :--- |
| **Account** | **Workers Scripts** | **Edit** | Men-deploy worker inbound/outbound |
| **Account** | **Workers KV Storage** | **Edit** | Penegakan kuota real-time di edge |
| **Account** | **R2 Storage** | **Edit** | Membuat dan mengelola bucket transit |
| **Account** | **Access: Apps and Policies** | **Edit** | Membuat bypass untuk jalur webhook email masuk saat Webmail dilindungi Cloudflare Access |
| **Zone** | **Email Routing** | **Edit** | Mengaktifkan routing dan mengelola aturan |
| **Zone** | **DNS** | **Edit** | Membuat record MX, SPF, DMARC, dan DKIM |

> **Catatan Keamanan:** Sangat disarankan untuk membatasi "Account Resources" dan "Zone Resources" token ini hanya pada akun dan domain spesifik yang ingin Anda gunakan dengan DockFlare.

## Persyaratan Sistem

*   **DockFlare:** v3.1.0 atau lebih baru.
*   **Docker:** v20.10+.
*   **Docker Compose:** v2.20+ (diperlukan untuk dukungan `profiles`).
*   **Penyimpanan:** Pastikan ada ruang disk yang cukup di mesin host untuk volume `mail_data`, yang akan menyimpan semua database email dan lampiran.
