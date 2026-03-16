# Monitoring dengan Prometheus & Grafana

Agent `cloudflared` yang dikelola DockFlare dapat mengekspos berbagai metrik performa dan kesehatan dalam format Prometheus. Dengan mengumpulkan dan memvisualisasikan metrik ini, Anda bisa mendapatkan wawasan penting tentang trafik tunnel, latensi, dan error rate.

Panduan ini menjelaskan cara mengaktifkan endpoint metrik dan menyiapkan stack monitoring cepat dengan Prometheus dan Grafana.

## Langkah 1: Aktifkan Metrics Endpoint di DockFlare

Langkah pertama adalah memberi tahu DockFlare agar mengaktifkan endpoint metrik Prometheus pada agent `cloudflared` yang dikelolanya.

Anda bisa melakukannya dengan menetapkan environment variable `CLOUDFLARED_METRICS_PORT` pada container DockFlare.

```yaml
services:
  dockflare:
    image: alplat/dockflare:stable
    # ... pengaturan lain
    environment:
      - CLOUDFLARED_METRICS_PORT=2000
```

Saat DockFlare direstart dengan variabel ini, DockFlare akan otomatis membuat ulang agent `cloudflared` internalnya dengan metrics server aktif pada port tersebut.

**Catatan:** fitur ini hanya tersedia pada **Internal Mode**. Jika Anda memakai [External Mode](External-cloudflared-Mode.md), Anda sendiri yang harus mengaktifkan metrics endpoint pada agent `cloudflared` Anda.

## Langkah 2: Siapkan Monitoring Stack

Jika Anda belum punya monitoring stack, Anda bisa menyiapkannya cepat dengan Docker Compose. Repository DockFlare menyediakan contoh setup pada direktori `/examples`.

Untuk panduan lengkap yang siap salin-tempel, lihat file **[`grafana quick setup.md`](https://github.com/ChrispyBacon-dev/DockFlare/blob/main/examples/grafana%20quick%20setup.md)** di repository.

Panduan itu mencakup:
1. Membuat struktur direktori yang diperlukan
2. Menambahkan service Prometheus dan Grafana ke `docker-compose.yml`
3. Mengonfigurasi Prometheus agar melakukan scrape metrik dari agent `cloudflared`
4. Menyediakan provisioning otomatis untuk Grafana dengan data source Prometheus

## Langkah 3: Import Dashboard Grafana yang Sudah Jadi

Agar visualisasi lebih mudah, DockFlare menyediakan dashboard Grafana yang sudah siap pakai.

1. Dashboard tersedia sebagai **[`dashboard.json`](https://github.com/ChrispyBacon-dev/DockFlare/blob/main/examples/dashboard.json)** di direktori `/examples`
2. Unduh file itu
3. Login ke instance Grafana Anda
4. Buka bagian **Dashboards** lalu klik **Import**
5. Upload `dashboard.json`
6. Pilih data source Prometheus Anda lalu import dashboard

Setelah itu Anda akan memiliki gambaran lengkap mengenai performa Cloudflare Tunnel, termasuk request count, error rate, latensi koneksi, dan lainnya.

![Grafana Dashboard Example](../static/images/grafana_dashboard_example.png)
