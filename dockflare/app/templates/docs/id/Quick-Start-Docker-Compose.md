# Quick Start (Docker Compose)

Panduan ini menjelaskan cara tercepat untuk menjalankan DockFlare dengan socket proxy yang diperkeras dan konfigurasi master rootless.

## Opsi A — Instalasi Satu Perintah (Direkomendasikan)

Cara tercepat untuk menjalankan DockFlare adalah menggunakan skrip instalasi interaktif yang tersedia di [dockflare.app](https://dockflare.app):

```bash
bash <(curl -fsSL https://dockflare.app/install.sh)
```

Skrip akan memandu Anda melalui:
1. Memilih direktori instalasi (default: `~/dockflare/`).
2. Memilih port UI lokal (default: `5000`).
3. Konfigurasi opsional tunnel Cloudflare untuk DockFlare.
4. Mengaktifkan profil email secara opsional (dockflare-mail-manager + dockflare-webmail).

Kemudian menghasilkan `docker-compose.yml`, memungkinkan Anda meninjaunya, dan meminta konfirmasi sebelum memulai stack.

Setelah berjalan, buka `http://<your-server-ip>:5000` dan selesaikan wizard pengaturan.

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
    logging:
      driver: "none"
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
    command: ["sh", "-c", "chown -R ${DOCKFLARE_UID:-65532}:${DOCKFLARE_GID:-65532} /app/data"]
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
      - "5000:5000" # Optional: comment out once exposed via Cloudflare Tunnel with an Access Policy to restrict access to tunnel-only
    #labels: # -- Cloudflare Tunnel Configuration (via DockFlare) OPTIONAL --
      # Main DockFlare with access policy
      #- dockflare.enable=true
      #- dockflare.hostname=dockflare.TLD  # replace with your domain
      #- dockflare.service=http://dockflare:5000
      #- dockflare.access.group=YOUR-ACCESS-GROUP-ID  # your custom access policy
      # -- OAuth Callback Path (Bypass Access Policy) OPTIONAL --
      # Required if using OAuth authentication with access policies on main interface
      #- dockflare.0.hostname=dockflare.example.tld
      #- dockflare.0.path=/auth/google/callback
      #- dockflare.0.service=http://dockflare:5000
      #- dockflare.0.access.group=public-default-bypass

      # Add additional callback paths for other OAuth providers as needed
      # - dockflare.1.hostname=dockflare.example.com
      # - dockflare.1.path=/auth/github/callback
      # - dockflare.1.service=http://dockflare:5000
      # - dockflare.1.access.group=public-default-bypass
    volumes:
      - dockflare_data:/app/data
    environment:
      - REDIS_URL=redis://redis:6379/0
      - REDIS_DB_INDEX=0
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
    logging:
      driver: "none"
    volumes:
      - dockflare_redis:/data
    networks:
      - dockflare-internal

  dockflare-mail-manager:
    image: alplat/dockflare-mail-manager:stable
    container_name: dockflare-mail-manager
    restart: unless-stopped
    profiles: ["email"]
    environment:
      - DOCKFLARE_MASTER_URL=http://dockflare:5000
      - MAIL_DATA_PATH=/data
    volumes:
      - mail_data:/data
    depends_on:
      dockflare:
        condition: service_started
    networks:
      - cloudflare-net
      - dockflare-internal

  dockflare-webmail:
    image: alplat/dockflare-webmail:stable
    container_name: dockflare-webmail
    restart: unless-stopped
    profiles: ["email"]
    environment:
      - DOCKFLARE_MASTER_URL=https://dockflare.TLD  # replace with your domain
    labels:
      - dockflare.enable=true
      - dockflare.hostname=mail.dockflare.TLD  # replace with your domain
      - dockflare.service=http://dockflare-webmail:80
    depends_on:
      dockflare-mail-manager:
        condition: service_started
    networks:
      - cloudflare-net
      - dockflare-internal

volumes:
  dockflare_data:
  dockflare_redis:
  mail_data:

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
