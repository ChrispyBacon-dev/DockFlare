# DockFlare Agent & Arsitektur Multi-Server

DockFlare 3.0 memperkenalkan model eksekusi terdistribusi yang memungkinkan Anda mengelola Cloudflare Tunnel di banyak host Docker. DockFlare **Master** mengoordinasikan konfigurasi, sementara **Agent** yang ringan berjalan di dekat workload Anda dan menjaga instance `cloudflared` lokalnya tetap sinkron dengan master.

Panduan ini menjelaskan arsitektur, model keamanan, dan alur langkah demi langkah untuk melakukan deployment agent.

---

## Mengapa Agent?

* **Memisahkan compute dari ingress** – workload tetap dekat dengan pengguna, tetapi kontrol tetap terpusat.
* **Visibilitas per host** – pantau heartbeat, status tunnel, dan riwayat command untuk setiap agent.
* **Token least-privilege** – agent yang kompromi bisa dicabut tanpa menyentuh master atau host lain.
* **Update yang tangguh** – agent tetap melayani trafik dengan konfigurasi terakhir yang diketahui meski master sedang tidak tersedia sementara.

---

## Komponen Singkat

| Komponen | Tanggung jawab |
|-----------|----------------|
| **Master (DockFlare)** | Menyediakan web UI, menyimpan state, merekonsiliasi desired ingress rules, dan mengeluarkan command. |
| **Redis** | Backplane untuk caching, heartbeat agent, dan command queue. |
| **DockFlare Agent** | Container headless yang memantau event Docker lokal, mengeksekusi command, dan menjalankan `cloudflared`. |
| **cloudflared** | Menangani koneksi tunnel aktual ke Cloudflare untuk masing-masing agent. |

Master dan Redis biasanya berjalan bersama, sementara agent berjalan di dekat workload, termasuk pada jaringan remote.

---

## Prasyarat

* DockFlare Master ≥ v3.0 dengan Redis terkonfigurasi (`REDIS_URL` di-set). Secara opsional gunakan `REDIS_DB_INDEX` agar data terisolasi dari container lain yang memakai instance Redis yang sama.
* Cloudflare API token dengan permission Tunnel + Access, sama seperti versi sebelumnya.
* Runtime Docker pada setiap host yang ingin Anda kelola.
* (Opsional) Segmen jaringan khusus atau VPN antara master dan agent jika Anda tidak mengekspos master secara publik.

---

## Gambaran Alur

1. **Generate agent API key** di UI DockFlare (`Agents → Generate Key`).
2. **Deploy DockFlare Agent** di host remote, sambil meneruskan URL master dan key.
3. Agent akan **register** ke master dan muncul dengan status *Pending*.
4. Dari UI master, **enrol** agent tersebut dan tetapkan atau buat Cloudflare Tunnel untuk host itu.
5. Master mengantrekan command; agent melakukan **poll**, menerapkan konfigurasi, dan melaporkan status/heartbeat. DockFlare mendeteksi zone target untuk tiap hostname secara otomatis, lalu hanya fallback ke default zone jika deteksi gagal.
6. Saat container start/stop di host agent, agent mengalirkan event ke master yang lalu memperbarui DNS, Access Policy, dan ingress rule tunnel.

---

## Deploy DockFlare Agent

> ℹ️ Agent akan dipublikasikan sebagai `alplat/dockflare-agent`. Sampai repository publiknya tersedia, Anda bisa build dari source tree `DockFlare-agent` yang disertakan bersama DockFlare 3.0.

```bash
# Contoh file environment yang dipakai container agent
DOCKFLARE_MASTER_URL=https://dockflare.example.com
DOCKFLARE_API_KEY=agent_api_key_goes_here
DOCKER_HOST=tcp://docker-socket-proxy:2375
# mengontrol image Docker yang dipakai untuk tunnel cloudflared yang dikelola
CLOUDFLARED_IMAGE=cloudflare/cloudflared:2025.9.0
LOG_LEVEL=info
TZ=Europe/Zurich
```

`docker-compose.yml` minimal di host agent:

```yaml
version: '3.8'

services:
  docker-socket-proxy:
    image: tecnativa/docker-socket-proxy:v0.4.1
    container_name: docker-socket-proxy
    restart: unless-stopped
    environment:
      - DOCKER_HOST=unix:///var/run/docker.sock
      - CONTAINERS=1
      - EVENTS=1
      - NETWORKS=1
      - IMAGES=1
      - POST=1
      - PING=1
      - EXEC=1
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock
    networks:
      - dockflare-internal

  dockflare-agent:
    image: alplat/dockflare-agent:latest
    container_name: dockflare-agent
    restart: unless-stopped
    env_file:
      - .env
    environment:
      - DOCKER_HOST=${DOCKER_HOST:-tcp://docker-socket-proxy:2375}
      - TZ=${TZ:-UTC}
      - LOG_LEVEL=${LOG_LEVEL:-info}
    volumes:
      - agent_data:/app/data
    depends_on:
      - docker-socket-proxy
    networks:
      - cloudflare-net
      - dockflare-internal

volumes:
  agent_data:

networks:
  cloudflare-net:
    name: cloudflare-net
    external: true
  dockflare-internal:
    name: dockflare-internal
```

- Jalankan `docker network create cloudflare-net` sekali untuk menyiapkan shared network yang dipakai master dan agent.
- Socket proxy membatasi permukaan Docker API yang bisa dijangkau agent; hanya capability yang diset `1` yang akan terekspos.
- Image agent berjalan sebagai user tanpa hak istimewa `dockflare` (UID/GID 65532). Pastikan mounted directory seperti `/app/data` bisa ditulis oleh akun tersebut, atau rebuild dengan `DOCKFLARE_UID/DOCKFLARE_GID` agar cocok dengan host.
- Isi file `.env` dengan `DOCKFLARE_MASTER_URL` dan `DOCKFLARE_API_KEY`; override opsional seperti `LOG_LEVEL` atau `DOCKER_HOST` bisa diberikan dengan cara yang sama.

---

## Model Keamanan

* **Master API key** – melindungi administrative API. UI hanya menampilkannya setelah Anda mengklik *Show master API key*.
* **Agent API keys** – unik untuk tiap agent. Jika key dicabut, pendaftaran atau command lebih lanjut dari host tersebut akan langsung diblokir.
* **Redis** – dipakai untuk queue dan cache; amankan dengan password dan network ACL jika berjalan di luar LAN tepercaya.
* **Transport** – jalankan master di balik HTTPS, misalnya lewat Cloudflare Access, agar trafik agent terenkripsi.
* **Runtime least-privilege** – container agent berjalan sebagai user `dockflare` (UID/GID 65532) dan mengandalkan socket proxy untuk membatasi akses Docker hanya ke inspeksi container dan kontrol lifecycle.

### Hardening yang Direkomendasikan

1. Simpan agent key di vault atau password manager, dan rotasi secara berkala.
2. **Jangan menonaktifkan password login** - gunakan OAuth/OIDC provider untuk SSO yang nyaman tanpa risiko keamanan. Jika Anda tetap harus mematikannya, pahami bahwa ini menciptakan kerentanan pada jaringan Docker karena container lain di network yang sama dapat melewati autentikasi eksternal. Lihat [Accessing the Web UI - Disabling Password Login](Accessing-the-Web-UI.md#menonaktifkan-login-dengan-password) untuk implikasi lengkapnya.
3. Gunakan tunnel terpisah per agent untuk isolasi least-privilege.
4. Pantau halaman `Agents` untuk heartbeat yang hilang; node offline bisa dihapus langsung dari UI.

---

## Troubleshooting

| Gejala | Solusi |
|---------|-----|
| Agent tersangkut di `pending` | Pastikan agent mendaftar dengan API key yang benar dan lakukan enrol dari UI. |
| Command tidak pernah selesai | Konfirmasi konektivitas Redis dan sinkronisasi jam container agent. |
| DNS tidak diperbarui | Master harus bisa mencapai Cloudflare dan agent harus mengirim event container; periksa `docker logs dockflare-agent`. |
| Heartbeat offline | Cek jalur jaringan antara agent dan master; firewall atau masalah TLS sering jadi penyebab. |

---

## Langkah Berikutnya

* Tinjau Quick Start yang diperbarui di README repository agar Redis dipastikan terkonfigurasi.
* Periksa changelog untuk breaking changes dan catatan migrasi.
* Ikuti repository publik DockFlare Agent saat sudah dipublikasikan agar tetap up to date dengan rilis terbaru.

Selamat bertunneling.
