# Berpindah Antar Mode

Anda dapat memindahkan DockFlare antara mode **Internal** dan **External** `cloudflared` kapan saja. Panduan ini menjelaskan proses transisinya agar berjalan mulus.

Untuk perbandingan rinci kedua mode tersebut, lihat [Internal vs. External `cloudflared`](Internal-vs-External-cloudflared.md).

---

## Beralih dari Internal ke External Mode

Proses ini melibatkan penyiapan agent `cloudflared` Anda sendiri lalu memberi tahu DockFlare untuk memakainya.

**Langkah 1: Siapkan agent `cloudflared` eksternal**

Pastikan agent itu:
* memakai Cloudflare Tunnel tertentu
* Anda mencatat **Tunnel ID** atau UUID-nya
* agent berjalan dengan benar dan terlihat **connected** di dashboard Cloudflare

**Langkah 2: Ubah konfigurasi dan restart DockFlare**

Di `docker-compose.yml`:

```yaml
services:
  dockflare:
    image: alplat/dockflare:stable
    environment:
      - USE_EXTERNAL_CLOUDFLARED=true
      - EXTERNAL_TUNNEL_ID=your-tunnel-uuid-goes-here
```

**Langkah 3: Deploy perubahan**

Jalankan `docker compose up -d` untuk membuat ulang container DockFlare.

Saat container aktif kembali:
1. DockFlare mendeteksi `USE_EXTERNAL_CLOUDFLARED=true`
2. DockFlare akan **menghentikan dan menghapus** `cloudflared-agent` internalnya
3. Semua ingress rule akan dikirim ke tunnel pada `EXTERNAL_TUNNEL_ID`

---

## Beralih dari External ke Internal Mode

Proses ini lebih sederhana karena Anda hanya membiarkan DockFlare mengambil alih kembali.

**Langkah 1: Ubah konfigurasi DockFlare**

Hapus environment variable external mode dari `docker-compose.yml`:

```yaml
services:
  dockflare:
    image: alplat/dockflare:stable
    environment:
      # Hapus dua baris berikut
      # - USE_EXTERNAL_CLOUDFLARED=true
      # - EXTERNAL_TUNNEL_ID=your-tunnel-uuid-goes-here
```

**Langkah 2: Deploy perubahan**

Jalankan `docker compose up -d`.

Saat container mulai:
1. DockFlare mendeteksi `USE_EXTERNAL_CLOUDFLARED` tidak aktif
2. DockFlare otomatis **membuat, mengonfigurasi, dan menjalankan** container internal `cloudflared-agent`
3. Agent baru itu akan memakai tunnel name yang didefinisikan di pengaturan DockFlare

**Langkah 3: Nonaktifkan agent eksternal Anda**

Setelah agent internal dipastikan berjalan dengan baik dan trafik normal, Anda bisa menghentikan dan menghapus agent `cloudflared` eksternal Anda.
