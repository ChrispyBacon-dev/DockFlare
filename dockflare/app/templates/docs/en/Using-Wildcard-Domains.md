# Using Wildcard Domains

DockFlare supports using wildcard domains (e.g., `*.example.com`) to route traffic for multiple subdomains to a single service. This is particularly useful for applications that handle dynamic subdomains, such as multi-tenant services or personal dashboards like Heimdall.

## How It Works

When you use a wildcard hostname, Cloudflare Tunnel will route all traffic for any subdomain that doesn't have a more specific DNS record to the service you specify.

For example, if you configure `*.apps.example.com`, traffic for `service1.apps.example.com`, `service2.apps.example.com`, and so on will all be routed to the same destination container.

## Important Considerations

Unlike regular hostnames, DockFlare **cannot automatically create DNS records for wildcard domains**. You must create the wildcard DNS record manually in your Cloudflare dashboard.

DockFlare will still manage the **ingress rule** in your Cloudflare Tunnel, but the initial DNS setup is a manual step.

## Step-by-Step Guide

Here is how to correctly set up a wildcard domain with DockFlare, using `*.plex.example.com` as an example.

### Step 1: Manually Create the Wildcard DNS Record

1.  Log in to your **Cloudflare Dashboard**.
2.  Navigate to the DNS settings for your domain.
3.  Click **Add record** and create a CNAME record with the following details:
    *   **Type:** `CNAME`
    *   **Name:** `*.plex` (or just `*` if your main domain is `plex.example.com`)
    *   **Target:** Your tunnel's public hostname. You can find this in your Cloudflare Zero Trust dashboard under **Access -> Tunnels**. It will look something like `your-tunnel-uuid.cfargotunnel.com`.
    *   **Proxy status:** Make sure it is **Proxied** (orange cloud).

    This manual DNS record tells Cloudflare to send all traffic for `*.plex.example.com` to your tunnel.

### Step 2: Configure Your Service with a Wildcard Label

Now, configure your service in your `docker-compose.yml` file with a wildcard hostname label.

```yaml
services:
  my-proxy-manager:
    image: nginxproxymanager/nginx-proxy-manager
    restart: unless-stopped
    networks:
      - cloudflare-net
    labels:
      - "dockflare.enable=true"
      # Use the wildcard hostname here
      - "dockflare.hostname=*.plex.example.com"
      - "dockflare.service=http://my-proxy-manager:81"
```

### Step 3: Deploy and Verify

1.  Save your `docker-compose.yml` file and run `docker compose up -d`.
2.  DockFlare will detect the container and create an ingress rule in your Cloudflare Tunnel for the hostname `*.plex.example.com`.
3.  You can verify this in the DockFlare Web UI and in your tunnel's configuration in the Cloudflare dashboard.

Now, any request to a subdomain like `sonarr.plex.example.com` or `radarr.plex.example.com` will be routed through your Cloudflare Tunnel to your `my-proxy-manager` container, which can then handle the traffic accordingly.
