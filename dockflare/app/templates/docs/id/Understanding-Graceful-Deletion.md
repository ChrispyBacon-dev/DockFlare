# Memahami Graceful Deletion

Saat Anda menghentikan container yang dikelola DockFlare, Anda mungkin melihat hostname publiknya tidak langsung offline. Itu terjadi karena fitur **Graceful Deletion**.

## Apa itu Graceful Deletion?

Alih-alih langsung menghapus ingress rule Cloudflare dan DNS record saat container berhenti, DockFlare menandai rule tersebut sebagai **"pending deletion"** lalu memulai timer.

Resource Cloudflare terkait hanya akan dihapus permanen setelah timer ini, yang disebut **grace period**, habis.

## Mengapa Ini Berguna?

Fitur ini dirancang untuk mencegah gangguan layanan dalam skenario operasional umum:

*   **Update container:** saat Anda menjalankan `docker compose up -d`, Docker biasanya menghentikan container lama lalu menyalakan yang baru. Dengan grace period, DNS record dan ingress rule tetap aktif sehingga tidak terjadi downtime.
*   **Restart sementara:** jika Anda menghentikan container sebentar untuk mengubah pengaturan lalu menyalakannya lagi, grace period memastikan konfigurasi publik tetap utuh.

## Variabel `GRACE_PERIOD_SECONDS`

Durasi grace period dikendalikan oleh environment variable `GRACE_PERIOD_SECONDS` di `docker-compose.yml`.

*   Nilai default: `600` detik atau 10 menit
*   Anda dapat menyesuaikannya sesuai kebutuhan

```yaml
services:
  dockflare:
    image: alplat/dockflare:stable
    environment:
      - GRACE_PERIOD_SECONDS=3600
```

## Cara Kerjanya dalam Praktik

1. **Container berhenti:** Anda menjalankan `docker stop my-app`
2. **Pending deletion:** DockFlare mendeteksi event stop, dan di Web UI rule akan tampil dengan status `pending_deletion`
3. **Dua skenario:**
    *   **Grace period habis:** DockFlare menjalankan cleanup dan menghapus ingress rule serta CNAME record
    *   **Container hidup lagi:** jika container dijalankan lagi sebelum grace period habis, DockFlare akan membatalkan penghapusan dan mengembalikan status ke `active`
