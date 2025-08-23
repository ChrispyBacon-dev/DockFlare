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
  dockflare:
    image: alplat/dockflare:stable
    container_name: dockflare
    restart: unless-stopped
    ports:
      - "5000:5000"
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock:ro
      - ./dockflare_data:/app/data
    networks:
      - cloudflare-net

  # Add your new service here
  nginx-webserver:
    image: nginx:latest
    container_name: my-nginx
    restart: unless-stopped
    networks:
      - cloudflare-net # Must be on the same network as DockFlare
    labels:
      # --- DockFlare Configuration ---
      - "dockflare.enable=true"
      - "dockflare.hostname=nginx.example.com"
      - "dockflare.service=http://nginx-webserver:80"

volumes:
  dockflare_data:

networks:
  cloudflare-net:
    name: cloudflare-net
    external: true
```

### 2. Understanding the Labels

*   `dockflare.enable=true`: This tells DockFlare to manage this container.
*   `dockflare.hostname=nginx.example.com`: This is the public URL where your service will be available. DockFlare will create a DNS record for this hostname in your Cloudflare account.
*   `dockflare.service=http://nginx-webserver:80`: This tells Cloudflare Tunnel where to send the traffic. It's the internal address of the NGINX container. Note that we are using the service name (`nginx-webserver`) as the hostname, which is possible because both containers are on the same Docker network.

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
