# Debugging & Log

Saat melakukan troubleshooting pada DockFlare, alat utama Anda adalah log dari container DockFlare dan agent `cloudflared` yang dikelolanya.

## 1. Memeriksa Log Container DockFlare

Sumber informasi terpenting adalah output log dari container DockFlare sendiri. Log ini memberikan gambaran detail dan real-time tentang apa yang sedang dilakukan DockFlare.

### Apa yang Ada di Log:
*   deteksi event start/stop container Docker
*   pemrosesan label `dockflare.*`
*   panggilan ke Cloudflare API
*   pesan sukses atau error detail dari Cloudflare API
*   status background task seperti cleanup resource

### Cara Melihat Log:

```bash
# Lihat seluruh riwayat log
docker logs dockflare

# Ikuti log secara real-time
docker logs -f dockflare
```

## 2. Menggunakan Real-time Log di Web UI

Untuk kenyamanan, dashboard DockFlare memiliki **real-time log viewer** di bagian bawah halaman utama.

Viewer ini menampilkan log yang sama dengan `docker logs -f dockflare`, tetapi lebih nyaman untuk memantau apa yang terjadi saat itu juga tanpa keluar dari browser.

## 3. Memeriksa Log Agent `cloudflared`

Jika Anda mencurigai masalah ada pada koneksi antara server Anda dan jaringan Cloudflare, periksa log container agent `cloudflared` secara langsung.

### Cara Melihat Log Agent:

Secara default, nama container agent adalah `cloudflared-agent-<tunnel-name>`. Anda bisa menemukan nama pastinya dengan `docker ps`.

```bash
docker logs cloudflared-agent-dockflare-tunnel
```

Log ini berguna untuk mendiagnosis:
*   error koneksi ke edge Cloudflare
*   masalah autentikasi pada tunnel token
*   error level protokol pada trafik yang diproksikan

**Catatan:** ini hanya berlaku pada **Internal Mode**. Jika memakai [External Mode](External-cloudflared-Mode.md), periksa log agent `cloudflared` milik Anda sendiri.

## 4. Memeriksa Dashboard Cloudflare

Jangan lupa menggunakan dashboard Cloudflare sebagai alat debugging:
*   **DNS Page:** cek apakah CNAME record dibuat seperti yang diharapkan
*   **Zero Trust Dashboard → Access -> Tunnels:** cek status tunnel dan ingress rules
*   **Zero Trust Dashboard → Access -> Applications:** cek konfigurasi dan kesehatan Zero Trust policy
