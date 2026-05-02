# Quick Start (Docker Compose)

This guide walks through the fastest way to run DockFlare with the hardened socket proxy and rootless master configuration.

## Option A — One-Liner Install (Recommended)

The quickest way to get DockFlare running is the interactive install script hosted at [dockflare.app](https://dockflare.app):

```bash
bash <(curl -fsSL https://dockflare.app/install.sh)
```

The script will guide you through:
1. Choosing an install directory (default: `~/dockflare/`).
2. Choosing a local UI port (default: `5000`).
3. Optionally configuring a Cloudflare Tunnel for DockFlare itself.
4. Optionally enabling the Email profile (dockflare-mail-manager + dockflare-webmail).

It then writes `docker-compose.yml`, lets you review it, and asks before pulling and starting the stack.

Once running, open `http://<your-server-ip>:5000` and complete the setup wizard.

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
