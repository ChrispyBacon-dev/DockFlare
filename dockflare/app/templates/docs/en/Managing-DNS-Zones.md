# Managing DNS Zones

DockFlare is capable of managing DNS records across multiple domains (Cloudflare Zones) within the same Cloudflare account. This allows you to run services on `service-a.domain-one.com` and `service-b.another-domain.org` from the same DockFlare instance.

## Default Zone

During initial setup, you provide a **Zone ID** used as a compatibility default. DockFlare normally loads every active zone accessible to the configured account and selects the longest DNS-label suffix matching each complete hostname. The default is used without verification only when the zone inventory is temporarily unavailable.

For example, `app.internal.side.co.uk` selects `internal.side.co.uk` when both that nested zone and `side.co.uk` are accessible. DockFlare does not assume that the final two hostname labels form the zone.

The master performs the same resolution for local Docker containers, agent-reported containers, manual rules, API-created rules, and reconciliation. Existing agents do not require a protocol or image update for this behavior.

## Overriding the Zone with a Label

To select a particular containing zone explicitly, use the `dockflare.zonename` label.

The explicit zone must exist in the configured Cloudflare account and must contain the hostname. An invalid or unrelated explicit zone causes the rule to be rejected; DockFlare does not silently fall back to another zone.

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

DockFlare automatically includes zones referenced by active rules when scanning tunnel DNS records. You can use `TUNNEL_DNS_SCAN_ZONE_NAMES` to include additional zones that do not currently have an active DockFlare rule.

### `TUNNEL_DNS_SCAN_ZONE_NAMES`

This environment variable accepts a comma-separated list of extra zone names that the UI should scan when looking for DNS records.

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
