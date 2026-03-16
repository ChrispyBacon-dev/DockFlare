# `cloudflared` Internal vs Eksternal

DockFlare dapat berjalan dalam dua mode untuk mengelola agent `cloudflared`, yaitu perangkat lunak yang membuat koneksi persisten antara server Anda dan jaringan Cloudflare. Memahami dua mode ini penting untuk memilih setup yang tepat.

## Internal Mode (Default)

Pada Internal Mode, DockFlare sepenuhnya bertanggung jawab mengelola agent `cloudflared`.

### Cara Kerjanya
Saat DockFlare berjalan, ia akan otomatis:
1. Membuat container Docker khusus yang menjalankan image `cloudflare/cloudflared`
2. Mengonfigurasi container agent agar terhubung ke akun Cloudflare Anda dan memakai tunnel yang ditentukan pada pengaturan DockFlare
3. Memastikan agent tetap berjalan dan merestartnya jika gagal
4. Menerapkan pengaturan relevan seperti endpoint metrik Prometheus

Ini adalah mode **default dan yang direkomendasikan** untuk sebagian besar pengguna.

### Kelebihan
*   **Sederhana:** nyaris tanpa konfigurasi
*   **Kompatibilitas terjamin:** DockFlare memastikan agent dikonfigurasi dengan cara yang didukung
*   **Manajemen terpusat:** semua yang terkait tunnel dikelola DockFlare

### Kekurangan
*   **Kontrol lebih sedikit:** Anda hanya bisa mengatur `cloudflared` sejauh yang diekspos DockFlare

---

## External `cloudflared` Mode

Pada External Mode, Anda sendiri yang menjalankan dan mengelola agent `cloudflared`. DockFlare akan terhubung ke agent yang sudah ada itu dan tidak membuat agent baru.

### Cara Kerjanya

DockFlare **tidak** akan membuat container `cloudflared`. Sebaliknya, DockFlare mengasumsikan Anda sudah menjalankan `cloudflared` sendiri, misalnya:
*   sebagai proses pada host OS
*   sebagai container yang Anda kelola sendiri
*   sebagai agent pada mesin lain

Ini adalah mode **lanjutan** untuk pengguna dengan kebutuhan khusus atau setup yang sudah kompleks.

### Kelebihan
*   **Kontrol maksimum:** versi, argumen command line, dan lifecycle sepenuhnya di tangan Anda
*   **Cocok untuk setup yang sudah ada**
*   **Lifecycle terpisah:** DockFlare dan `cloudflared` tidak saling terikat

### Kekurangan
*   **Lebih kompleks**
*   **Ada overhead konfigurasi tambahan**

### Cara Mengaktifkan External Mode

Atur environment variable berikut pada container DockFlare:

*   `USE_EXTERNAL_CLOUDFLARED=true`
*   `EXTERNAL_TUNNEL_ID` diisi UUID tunnel yang dipakai agent eksternal Anda

Saat variabel ini aktif, DockFlare akan melewati manajemen agent internal dan mengirim semua konfigurasi ingress rule ke tunnel yang ditentukan oleh `EXTERNAL_TUNNEL_ID`.
