# Health Check

DockFlare menyediakan endpoint health check khusus yang bisa digunakan dengan mekanisme health check bawaan Docker. Dengan begitu, Docker dapat memantau kesehatan aplikasi DockFlare dan merestartnya otomatis jika tidak responsif.

## Endpoint `/ping`

DockFlare mengekspos endpoint HTTP sederhana di `/ping`.

*   **Tujuan:** memberi cara sederhana bagi sistem otomatis untuk memeriksa apakah web server DockFlare berjalan dan responsif
*   **Autentikasi:** endpoint ini **tidak memerlukan autentikasi**
*   **Healthy response:** DockFlare yang sehat akan merespons `/ping` dengan **HTTP 200 OK**
*   **Informasi versi:** body respons juga memuat versi DockFlare yang sedang berjalan

## Cara Mengonfigurasi Health Check di Docker Compose

Anda bisa menambahkan bagian `healthcheck` ke service `dockflare` di `docker-compose.yml`:

```yaml
services:
  dockflare:
    image: alplat/dockflare:stable
    container_name: dockflare
    restart: unless-stopped
    # ... pengaturan lain
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:5000/ping"]
      interval: 1m30s
      timeout: 10s
      retries: 3
      start_period: 40s
```

### Penjelasan konfigurasi `healthcheck`

*   `test`: perintah yang dijalankan Docker di dalam container
*   `interval`: health check dijalankan setiap 90 detik
*   `timeout`: waktu tunggu maksimal 10 detik
*   `retries`: jika gagal 3 kali berturut-turut, container ditandai `unhealthy`
*   `start_period`: Docker menunggu 40 detik setelah start sebelum menjalankan health check pertama

Dengan konfigurasi ini, Anda bisa mengecek status container lewat `docker ps`. Jika container menjadi tidak sehat, Docker akan merestartnya sesuai kebijakan `restart`.
