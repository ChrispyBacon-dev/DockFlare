# Menggunakan Web UI

DockFlare Web UI adalah alat yang kuat untuk mengelola, memantau, dan mengonfigurasi layanan Anda. Antarmuka ini menyediakan cara yang nyaman untuk pekerjaan yang melampaui konfigurasi label Docker sederhana.

## Dashboard (Halaman Utama)

Halaman pertama setelah login adalah dashboard utama, pusat Anda untuk melihat state semua layanan yang dikelola.

*   **Managed Ingress Rules Table:** tabel ini menampilkan setiap ingress rule yang dikelola DockFlare, baik yang berasal dari container Docker maupun yang dibuat manual.
    *   **Hostname:** hostname publik layanan
    *   **Service:** URL tujuan internal
    *   **Source:** apakah rule berasal dari `Docker` atau dibuat `Manually`
    *   **Status:** `active`, `pending_deletion`, atau `UI Override`
    *   **Access:** menampilkan Access Group yang diterapkan dan badge mode
    *   **Manage Rule:** tombol untuk mengedit rule
*   **Real-time Logs:** di bawah tabel ada log viewer real-time dari backend DockFlare, sangat berguna untuk debugging.

## Mengelola Rule

UI memberi Anda kontrol penuh atas ingress rule:

*   **Add Manual Rule:** membuat ingress rule untuk layanan yang tidak berjalan di Docker, misalnya service di mesin lain pada LAN Anda
*   **Edit any Rule:** tombol **Manage Rule** membuka modal untuk mengubah konfigurasi rule apa pun
*   **Revert to Labels:** jika rule Docker punya UI override, tombol ini akan muncul agar rule kembali dikendalikan oleh label Docker

## Halaman Access Policies

Halaman ini adalah lokasi utama untuk mengelola **Access Groups** reusable dan mengamankan DNS zone dengan wildcard policy.

### Advanced Access Policies

Dari bagian Access Groups, Anda bisa:
*   **Create** Access Group baru dengan modal dua tab: Authenticated vs Public
*   **Edit** Access Group yang ada
*   **Delete** Access Group yang tidak lagi dipakai, kecuali system policy seperti `public-default-bypass`
*   **Sync from Cloudflare** untuk mengimpor reusable policy DockFlare yang sudah ada
*   Membuka policy terkait langsung di dashboard Cloudflare lewat ikon Cloudflare

**Catatan:** system policy `public-default-bypass` dibuat dan dikelola otomatis oleh DockFlare.

### Zone Default Policies (*.tld Wildcards)

Bagian kedua menampilkan **Zone Default Policies**, fitur best practice keamanan yang melindungi semua subdomain:

*   **Protection Status:** badge visual menunjukkan zone mana yang punya wildcard policy dan mana yang belum
*   **Create Zone Policy:** klik **Create Policy** pada zone yang belum terlindungi
*   **Select Policy:** pilih Access Group yang akan melindungi semua subdomain di zone tersebut
*   **Security Safety Net:** jika Anda lupa menambahkan policy pada service tertentu, wildcard policy tingkat zone akan menanganinya

**Praktik terbaik:** buat zone default policy untuk semua domain Anda. Untuk domain publik gunakan bypass default; untuk domain internal gunakan policy autentikasi.

Untuk detail lebih lanjut, lihat [Access Policy Best Practices & Examples](Access-Policy-Best-Practices.md).

## Halaman Settings

Halaman Settings berisi berbagai opsi administratif dan konfigurasi:

*   **Cloudflare Tunnels:** menampilkan semua Cloudflare Tunnel pada akun Anda, statusnya, dan agent `cloudflared` yang terhubung
*   **Backup & Restore:** unduh arsip backup DockFlare `.zip` atau upload arsip yang sudah diekspor sebelumnya untuk restore
*   **Security:**
    *   **Change Password:** ganti password Web UI
    *   **Disable Password Login:** untuk use case lanjutan di mana DockFlare berada di belakang authentication proxy lain. **⚠️ Peringatan:** ini menimbulkan risiko keamanan karena container lain pada jaringan Docker yang sama dapat melewati autentikasi eksternal
*   **Cloudflare Credentials:** memperbarui Cloudflare Account ID dan API Token
*   **Core Configuration:** mengubah pengaturan seperti Tunnel Name dan Rule Grace Period
