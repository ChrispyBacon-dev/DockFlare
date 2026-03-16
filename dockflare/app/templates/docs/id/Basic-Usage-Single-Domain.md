# Penggunaan Dasar (Satu Domain)

Panduan ini menunjukkan use case paling umum untuk DockFlare: mengekspos satu container Docker ke internet menggunakan satu hostname publik.

## Prasyarat

Sebelum mulai, pastikan Anda:
1. Telah menyelesaikan panduan [Quick Start](Quick-Start-Docker-Compose.md).
2. DockFlare sedang berjalan dan terhubung ke akun Cloudflare Anda.
3. Memiliki service yang ingin diekspos. Dalam contoh ini kita memakai `nginx`.

## Contoh: Mengekspos Container NGINX

Misalkan Anda ingin mengekspos web server NGINX standar pada hostname `nginx.example.com`.

### 1. Tambahkan service ke `docker-compose.yml`

Ubah file `docker-compose.yml` Anda agar mencakup service `nginx`. Kuncinya adalah menambahkan label `dockflare.*` ke konfigurasinya.

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
      - INFO=1
      - EXEC=1
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock
    networks:
      - dockflare-internal

  dockflare-init:
    image: alpine:3.20
    command: ["sh", "-c", "chown -R 65532:65532 /app/data"]
    volumes:
      - dockflare_data:/app/data
    networks:
      - dockflare-internal
    restart: "no"

  dockflare:
    image: alplat/dockflare:stable
    container_name: dockflare
    restart: unless-stopped
    ports:
      - "5000:5000"
    volumes:
      - dockflare_data:/app/data
    environment:
      - REDIS_URL=redis://redis:6379/0
      - REDIS_DB_INDEX=0  # Opsional: tentukan index database Redis (0-15) untuk isolasi dari container lain
      - DOCKER_HOST=tcp://docker-socket-proxy:2375
    depends_on:
      docker-socket-proxy:
        condition: service_started
      dockflare-init:
        condition: service_completed_successfully
      redis:
        condition: service_started
    networks:
      - cloudflare-net
      - dockflare-internal

  # Tambahkan service baru Anda di sini
  nginx-webserver:
    image: nginx:latest
    container_name: my-nginx
    restart: unless-stopped
    networks:
      - cloudflare-net
    labels:
      - "dockflare.enable=true"
      - "dockflare.hostname=nginx.example.com"
      - "dockflare.service=http://nginx-webserver:80"
      # Opsional: terapkan akses publik dengan bypass zone protection
      - "dockflare.access.group=public-default-bypass"

  redis:
    image: redis:7-alpine
    container_name: dockflare-redis
    restart: unless-stopped
    command: ["redis-server", "--save", "", "--appendonly", "no"]
    volumes:
      - dockflare_redis:/data
    networks:
      - dockflare-internal

volumes:
  dockflare_data:
  dockflare_redis:

networks:
  cloudflare-net:
    name: cloudflare-net
    external: true
  dockflare-internal:
    name: dockflare-internal
```

> **Mengapa Redis?** DockFlare bergantung pada Redis untuk caching, log streaming, dan messaging antar thread. Menjalankannya di jaringan privat `dockflare-internal` memastikan Redis hanya dapat diakses DockFlare, sementara workload tetap terisolasi di `cloudflare-net`.

### 2. Memahami Label

*   `dockflare.enable=true`: Memberi tahu DockFlare untuk mengelola container ini.
*   `dockflare.hostname=nginx.example.com`: Ini adalah URL publik tempat layanan Anda akan tersedia. DockFlare akan membuat DNS record untuk hostname ini di akun Cloudflare Anda.
*   `dockflare.service=http://nginx-webserver:80`: Memberi tahu Cloudflare Tunnel ke mana trafik harus dikirim. Ini adalah alamat internal container NGINX. Kita memakai nama service `nginx-webserver` sebagai hostname karena kedua container berada di jaringan Docker yang sama.
*   `dockflare.access.group=public-default-bypass`: (Opsional) Memakai system bypass policy untuk memastikan akses publik tetap terbuka meski ada wildcard policy `*.example.com` di level zone. Ini berguna saat domain Anda dilindungi wildcard policy tetapi ada service tertentu yang harus tetap publik.

### 3. Deploy Service

Simpan `docker-compose.yml` lalu jalankan perintah berikut untuk menyalakan service baru:

```bash
docker compose up -d
```

### 4. Verifikasi

DockFlare akan mendeteksi container baru dan otomatis melakukan hal berikut:
1. Menambahkan ingress rule ke Cloudflare Tunnel Anda untuk `nginx.example.com`.
2. Membuat CNAME record untuk `nginx.example.com` di Cloudflare DNS yang mengarah ke tunnel tersebut.

Anda bisa memverifikasinya dengan beberapa cara:
*   **DockFlare Web UI**: Service `nginx.example.com` akan muncul di dashboard.
*   **Cloudflare Dashboard**: Anda akan melihat CNAME record baru di DNS settings dan ingress rule baru pada konfigurasi tunnel.

Setelah DNS selesai propagasi, Anda seharusnya bisa membuka `https://nginx.example.com` di browser dan melihat halaman sambutan default NGINX.

## Backup & Restore Lebih Dalam

DockFlare menyediakan alur backup kelas satu agar Anda bisa memindahkan atau memulihkan instance dalam hitungan menit.

### Isi arsip backup

Saat Anda mengunduh backup dari **Settings → Backup & Restore** atau onboarding wizard, DockFlare akan menghasilkan file `.zip` yang berisi:

| File | Deskripsi |
| --- | --- |
| `dockflare_config.dat` | Payload konfigurasi terenkripsi seperti kredensial Cloudflare, hash password UI, default tunnel, master API key, dan lain-lain. |
| `dockflare.key` | Kunci Fernet untuk mendekripsi `dockflare_config.dat` dan payload terenkripsi lain. Simpan bersama arsip backup. |
| `agent_keys.dat` | Registry terenkripsi untuk agent API key, metadata, dan status pencabutan. |
| `state.json` | Snapshot JSON biasa dari runtime state, termasuk managed rules, agent, dan access group. Ini disertakan agar operator bisa memeriksa atau memigrasikan bagian tertentu jika dibutuhkan. |
| `manifest.json` | Checksum dan informasi versi untuk setiap file dalam arsip. |

Backup ini self-contained: saat dipulihkan lewat wizard atau endpoint restore, DockFlare menulis setiap file ke `/app/data/` lalu langsung menjadwalkan restart container agar konfigurasi terenkripsi dimuat ulang saat boot.

### Restore dan catatan kompatibilitas

- **Wizard & Settings UI**: Upload file `.zip` dan DockFlare akan mengimpornya, memuat ulang state, lalu keluar. Docker akan merestart container secara otomatis sehingga instance kembali operasional tanpa intervensi manual.
- **Legacy `state.json`**: Untuk troubleshooting atau alur lanjutan, Anda tetap bisa meng-upload hanya `state.json`. DockFlare akan mengisi runtime state dari file itu tetapi melewati konfigurasi terenkripsi; Anda harus memasukkan ulang kredensial setelahnya.
- **Otomasi**: Karena restart berlangsung otomatis, pastikan health check reverse proxy Anda mengizinkan jendela restart singkat sekitar 5 detik setelah restore.

Backup **tidak** menyertakan dataset Redis karena itu hanya cache yang bisa dibangun ulang oleh DockFlare. Volume `/app/data` dan arsip backup adalah bagian kritis yang harus diamankan.
