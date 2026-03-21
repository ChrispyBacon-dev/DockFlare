# Quick Start (Docker Compose)

This guide walks through the fastest way to run DockFlare with the hardened socket proxy and rootless master configuration.

## Option A — One-Liner Install (Recommended)

The quickest way to get DockFlare running is the install script hosted at [dockflare.app](https://dockflare.app):

```bash
curl -fsSL https://dockflare.app/install.sh | bash
```

The script will:
1. Check that Docker and Docker Compose are available.
2. Create `~/dockflare/` and write a `docker-compose.yml` there.
3. Create the `cloudflare-net` Docker network if it does not exist.
4. Pull the images and start all services.
5. Print the local URL when done.

Once running, open `http://<your-server-ip>:5000` and complete the setup wizard.

> **Optional overrides** — set environment variables before piping to control the install:
> ```bash
> DOCKFLARE_PORT=8080 DOCKFLARE_DIR=/opt/dockflare curl -fsSL https://dockflare.app/install.sh | bash
> ```

---

## Option B — Manual Docker Compose

If you prefer to manage the compose file yourself, follow the steps below.

### 1. Create the `docker-compose.yml` file

The stack below launches the docker-socket-proxy, primes the persistent volume with the correct ownership, and starts DockFlare alongside Redis.

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
      - REDIS_DB_INDEX=0  # Optional: specify Redis database index (0-15) for isolation from other containers
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

**Notes:**
- The master container runs as the `dockflare` user (UID/GID 65532). If you need to match different host permissions, set `DOCKFLARE_UID`/`DOCKFLARE_GID` and rebuild the image or adjust the init job.
- The proxy is mandatory. DockFlare never mounts `/var/run/docker.sock` directly, which limits the Docker API surface the master can reach.
- When using bind mounts instead of named volumes, make sure the target directory is writable by UID/GID 65532 (or your overridden values).
- Create the external network once if it does not exist: `docker network create cloudflare-net`.

### 2. Create the external network

If it does not exist yet:

```bash
docker network create cloudflare-net
```

### 3. Run DockFlare

Start the stack in detached mode:

```bash
docker compose up -d
```

This brings up the proxy, primes the volume, and launches DockFlare together with Redis.

### 4. Complete the Pre-Flight Setup

After the services are running, open your browser to `http://<your-server-ip>:5000`.

The **Pre-Flight Setup Wizard** walks you through:
1. Creating a password for the Web UI.
2. Entering your Cloudflare credentials (Account ID, Zone ID, API Token).
3. Configuring your initial Cloudflare Tunnel.
4. *(Optional)* Restoring from a DockFlare backup archive. If you already have a `dockflare_backup_*.zip`, choose **Restore from backup** before Step 1; the wizard imports your configuration and restarts the container automatically.

### 5. For Existing Users (Upgrading)

If you are upgrading from an older release, DockFlare detects the legacy `.env` file, migrates your configuration into the encrypted store, and guides you through password creation. Keep the socket proxy in place—direct mounts of `/var/run/docker.sock` are no longer supported.
