# Basic Usage (Single Domain)

This guide demonstrates the most common use case for DockFlare: exposing a single Docker container to the internet on a public hostname.

## Prerequisites

Before you start, make sure you have:
1.  Completed the [Quick Start](Quick-Start-Docker-Compose.md) guide.
2.  DockFlare is running and connected to your Cloudflare account.
3.  You have a service you want to expose (we will use `nginx` in this example).

## Example: Exposing an NGINX Container

Let's say you want to expose a standard NGINX web server at the hostname `nginx.example.com`.

### 1. Add the Service to your `docker-compose.yml`

Modify your `docker-compose.yml` file to include the `nginx` service. The key is to add the `dockflare.*` labels to its configuration.

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

  # Add your new service here
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
      # Optional: Apply public access with zone protection bypass
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
> **Why Redis?** DockFlare relies on Redis for caching, log streaming, and cross-thread messaging. Running it on the private `dockflare-internal` network keeps Redis reachable only by DockFlare, while workloads stay isolated on `cloudflare-net`.


### 2. Understanding the Labels

*   `dockflare.enable=true`: This tells DockFlare to manage this container.
*   `dockflare.hostname=nginx.example.com`: This is the public URL where your service will be available. DockFlare will create a DNS record for this hostname in your Cloudflare account.
*   `dockflare.service=http://nginx-webserver:80`: This tells Cloudflare Tunnel where to send the traffic. It's the internal address of the NGINX container. Note that we are using the service name (`nginx-webserver`) as the hostname, which is possible because both containers are on the same Docker network.
*   `dockflare.access.group=public-default-bypass`: (Optional) Uses the system bypass policy to ensure public access even if a zone-level `*.example.com` protection policy exists. This is important when you have wildcard policies protecting your domain but need specific services to remain public.

### 3. Deploy the Service

Save your `docker-compose.yml` file and run the following command to start the new service:

```bash
docker compose up -d
```

### 4. Verification

DockFlare will detect the new container and automatically perform the following actions:
1.  Add an ingress rule to your Cloudflare Tunnel for `nginx.example.com`.
2.  Create a CNAME record for `nginx.example.com` in your Cloudflare DNS, pointing to the tunnel.

You can verify this in a few ways:
*   **DockFlare Web UI**: The `nginx.example.com` service will appear on the dashboard.
*   **Cloudflare Dashboard**: You will see the new CNAME record in your DNS settings and the new ingress rule in your tunnel configuration.

After a few moments for DNS to propagate, you should be able to navigate to `https://nginx.example.com` in your browser and see the default NGINX welcome page.

## Backup & Restore Deep Dive

DockFlare ships with a first-class backup flow so you can move or recover an instance in minutes.

### What the backup archive contains

When you download a backup from **Settings → Backup & Restore** (or the onboarding wizard), DockFlare generates a `.zip` with the following files:

| File | Description |
| --- | --- |
| `dockflare_config.dat` | Encrypted configuration payload (Cloudflare credentials, UI password hash, tunnel defaults, master API key, etc.). |
| `dockflare.key` | The Fernet key used to decrypt `dockflare_config.dat` and other encrypted payloads. Keep it with the archive. |
| `agent_keys.dat` | Encrypted registry of agent API keys, metadata, and revocation status. |
| `state.json` | Plain JSON snapshot of runtime state—managed rules, agents, access groups. This is included so operators can inspect or migrate specific pieces if needed. |
| `manifest.json` | Checksums and versioning information for each file in the archive. |

The backup is self-contained: restoring it via the wizard/apply endpoint writes each file to `/app/data/` and immediately schedules a container restart so the encrypted configuration is reloaded on boot.

### Restoring and compatibility notes

- **Wizard & Settings UI**: Upload the `.zip` and DockFlare will import it, reload state, and exit. Docker restarts the container automatically, so you land back in operational mode without manual intervention.
- **Legacy `state.json`**: For troubleshooting or advanced workflows you can still upload just a `state.json` file. DockFlare will populate the runtime state from it but skip the encrypted config; you must re-enter credentials afterwards.
- **Automation**: Because the restart is automatic, make sure any reverse proxy health checks allow for a brief restart window (~5 s) after a restore.

Backups do **not** include the Redis dataset; it only caches data that DockFlare can recompute. The `/app/data` volume alongside the archive is the critical piece to secure and back up.
