# Managing DNS Zones

DockFlare is capable of managing DNS records across multiple domains (Cloudflare Zones) within the same Cloudflare account. This allows you to run services on `service-a.domain-one.com` and `service-b.another-domain.org` from the same DockFlare instance.

## Default Zone

During the initial setup of DockFlare, you provide a **Zone ID**. This is the **default zone** where DockFlare will create all DNS records. If you only plan to use a single domain, this is all you need to worry about.

## Overriding the Zone with a Label

To manage a service on a domain other than the default one, you can use the `dockflare.zonename` label.

This label tells DockFlare to create the DNS record for that specific service in the specified Cloudflare Zone.

### Prerequisites

For this to work, you must ensure that the **Cloudflare API Token** you are using has `Zone:DNS:Edit` permissions for **all the zones** you intend to manage.

### Example

Let's say your default zone is `example.com`, but you also want to run a service on `media.io`.

```yaml
services:
  # This service will be created in the default zone (example.com)
  service-one:
    image: nginx
    labels:
      - "dockflare.enable=true"
      - "dockflare.hostname=nginx.example.com"
      - "dockflare.service=http://service-one:80"

  # This service will be created in the 'media.io' zone
  service-two:
    image: portainer/portainer-ce
    labels:
      - "dockflare.enable=true"
      - "dockflare.hostname=portainer.media.io"
      - "dockflare.service=http://service-two:9000"
      # Override the default zone for this service
      - "dockflare.zonename=media.io"
```

When you deploy this, DockFlare will:
1.  Create a CNAME record for `nginx.example.com` in the `example.com` zone.
2.  Create a CNAME record for `portainer.media.io` in the `media.io` zone.

Both hostnames will be added as ingress rules to the same Cloudflare Tunnel.

## Viewing DNS Records in the UI

The DockFlare Web UI has a feature on the **Settings** page that allows you to view all Cloudflare Tunnels on your account and the DNS records pointing to them.

To ensure that the UI can find DNS records across all your different zones, you can use the `TUNNEL_DNS_SCAN_ZONE_NAMES` environment variable.

### `TUNNEL_DNS_SCAN_ZONE_NAMES`

This environment variable accepts a comma-separated list of zone names that the UI should scan when looking for DNS records.

**Example `docker-compose.yml`:**
```yaml
services:
  dockflare:
    image: alplat/dockflare:stable
    # ... other settings
    environment:
      # Tell the UI to scan these zones in addition to the default one
      - TUNNEL_DNS_SCAN_ZONE_NAMES=media.io,another-domain.org
```

This will ensure that the DNS record viewer in the UI provides a complete picture of all the domains pointing to your tunnels.
