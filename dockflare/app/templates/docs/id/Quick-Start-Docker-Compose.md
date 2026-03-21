# Quick Start (Docker Compose)

Panduan ini menjelaskan cara tercepat untuk menjalankan DockFlare dengan socket proxy yang diperkeras dan konfigurasi master rootless.

## Opsi A — Instalasi Satu Perintah (Direkomendasikan)

Cara tercepat untuk menjalankan DockFlare adalah menggunakan skrip instalasi yang tersedia di [dockflare.app](https://dockflare.app):

```bash
curl -fsSL https://dockflare.app/install.sh | bash
```

Skrip akan melakukan hal berikut:
1. Memeriksa bahwa Docker dan Docker Compose tersedia.
2. Membuat `~/dockflare/` dan menulis file `docker-compose.yml` di sana.
3. Membuat jaringan Docker `cloudflare-net` jika belum ada.
4. Menarik image dan memulai semua layanan.
5. Menampilkan URL lokal setelah selesai.

Setelah berjalan, buka `http://<your-server-ip>:5000` dan selesaikan wizard pengaturan.

> **Opsi kustomisasi** — atur variabel lingkungan sebelum menjalankan perintah untuk mengontrol instalasi:
> ```bash
> DOCKFLARE_PORT=8080 DOCKFLARE_DIR=/opt/dockflare curl -fsSL https://dockflare.app/install.sh | bash
> ```

---

## Opsi B — Docker Compose Manual

### 1. Buat file `docker-compose.yml`

Stack di bawah ini menjalankan `docker-socket-proxy`, menyiapkan persistent volume dengan ownership yang benar, dan menjalankan DockFlare bersama Redis.

```yaml
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

**Catatan:**
- Container master berjalan sebagai user `dockflare` (UID/GID 65532). Jika Anda perlu menyesuaikan dengan permission host yang berbeda, set `DOCKFLARE_UID`/`DOCKFLARE_GID` dan rebuild image atau sesuaikan init job.
- Proxy ini wajib. DockFlare tidak pernah me-mount `/var/run/docker.sock` secara langsung, sehingga permukaan Docker API yang bisa dijangkau master tetap terbatas.
- Saat memakai bind mount alih-alih named volume, pastikan direktori target bisa ditulis oleh UID/GID 65532 atau nilai override Anda.
- Buat external network sekali jika belum ada: `docker network create cloudflare-net`.

### 2. Buat external network

Jika belum ada:

```bash
docker network create cloudflare-net
```

### 3. Jalankan DockFlare

Jalankan stack dalam mode detached:

```bash
docker compose up -d
```

Perintah ini akan menyalakan proxy, menyiapkan volume, dan menjalankan DockFlare bersama Redis.

### 4. Selesaikan Pre-Flight Setup

Setelah service berjalan, buka browser ke `http://<your-server-ip>:5000`.

**Pre-Flight Setup Wizard** akan memandu Anda untuk:
1. Membuat password untuk Web UI.
2. Memasukkan kredensial Cloudflare Anda (Account ID, Zone ID, API Token).
3. Mengonfigurasi Cloudflare Tunnel pertama Anda.
4. *(Opsional)* Me-restore dari arsip backup DockFlare. Jika Anda sudah punya `dockflare_backup_*.zip`, pilih **Restore from backup** sebelum Step 1; wizard akan mengimpor konfigurasi dan merestart container secara otomatis.

### 5. Untuk Pengguna Lama (Upgrade)

Jika Anda melakukan upgrade dari rilis lama, DockFlare akan mendeteksi file `.env` lama, memigrasikan konfigurasi ke encrypted store, dan memandu Anda membuat password. Tetap gunakan socket proxy; mount langsung `/var/run/docker.sock` sudah tidak didukung lagi.
