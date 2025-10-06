# How DockFlare Works

DockFlare acts as a bridge between your Docker environment and the Cloudflare network, automating the process of exposing services securely to the internet. It continuously monitors your Docker host and uses the Cloudflare API to manage Tunnels, DNS records, and Access Policies on your behalf.

## Core Workflow

The core workflow can be broken down into a few key steps:

1.  **Docker Event Monitoring**: DockFlare listens for Docker socket events, such as `start` and `stop` for containers.

2.  **Label Detection**: When a new container is started, DockFlare inspects it for `dockflare.` labels. If a container has `dockflare.enable=true`, DockFlare knows it needs to manage it.

3.  **Cloudflare API Interaction**: Based on the labels, DockFlare communicates with the Cloudflare API to configure the necessary resources:
    *   **Cloudflare Tunnel**: It adds an ingress rule to your designated Cloudflare Tunnel. This rule points the public hostname to the container's internal network address (e.g., `http://my-app:8080`).
    *   **DNS Management**: It creates a CNAME DNS record in your Cloudflare DNS zone, pointing your desired public hostname (e.g., `my-app.example.com`) to your Cloudflare Tunnel.
    *   **Access Policies**: If you've specified access control labels, DockFlare creates or updates a reusable Cloudflare Access Policy to secure your service with Zero Trust rules (e.g., requiring a login from your identity provider or issuing a public `bypass`).

4.  **Automatic Cleanup**: When a managed container is stopped or removed, DockFlare automatically triggers a cleanup process. It removes the corresponding ingress rule from the Cloudflare Tunnel and, if no other service is using the hostname, deletes the DNS record and the Access Application. This prevents stale records and keeps your Cloudflare configuration clean.


## Components at a Glance

| Component | Responsibility |
| --- | --- |
| DockFlare Master | Hosts the UI and API, watches Docker events, and orchestrates Cloudflare tunnels, DNS, and Access policies. Runs rootless and only talks to Docker via the socket proxy. |
| Docker Socket Proxy | `tecnativa/docker-socket-proxy` sidecar that exposes the minimal Docker API surface (`containers`, `events`, etc.) to the master. Prevents the master from binding the raw Docker socket. |
| Redis | Caching, queues, log streaming, and agent heartbeat/backchannel. Lives on the private `dockflare-internal` network. |
| DockFlare Agents (optional) | Remote workers that mirror the master’s behaviour on other hosts, streaming Docker events back and managing their own `cloudflared`. |
| cloudflared | Maintains the tunnel connection to Cloudflare for either the master or each agent. |

## Layered Configuration Model

DockFlare uses a flexible, layered approach to configuration, giving you both automation and fine-grained control:

1.  **Docker Labels (Base Layer)**: This is the primary, automated method. You define a service's entire configuration—hostname, internal service URL, and access policy—directly in your `docker-compose.yml` or Docker run command. This is the "source of truth" for automated services.

2.  **Access Groups (Abstraction Layer)**: To avoid repeating complex access policies across many services, you can create reusable **Access Groups** in the Web UI. These are templates that bundle a set of access rules (e.g., "allow company emails" or "allow access from specific countries") and sync to named reusable Cloudflare Access Policies. The Public vs Authenticated toggle in the modal controls whether DockFlare emits a `bypass` or `allow` decision. You can then apply a whole policy to a container with a single label (`dockflare.access.group=my-policy-group`), simplifying your container labels significantly.

3.  **Web UI Overrides (Control Layer)**: The Web UI provides the ultimate level of control. From the dashboard, you can:
    *   **Override** the access policy of any service, whether it was defined by labels or an Access Group. These overrides are persistent and will not be undone by a container restart.
    *   **Create Manual Ingress Rules** for services that are not running in Docker (e.g., a service on another machine in your network).
    *   **Revert** a service's configuration back to what is defined in its Docker labels, discarding any UI overrides.

This layered model allows you to "set it and forget it" with Docker labels for most services, while still having the power to handle exceptions and complex scenarios through the Web UI.

---

## Access Policy Architecture (v3.0.3+)

### Reusable Policy System

DockFlare now uses a **reusable policy architecture** that aligns with Cloudflare's best practices:

1. **Access Groups** → Sync to → **Cloudflare Reusable Policies**
2. **Access Applications** → Reference → **Reusable Policy IDs**
3. **Single source of truth** - update once, applies everywhere

This architecture eliminates policy duplication and allows you to manage policies from either DockFlare or the Cloudflare dashboard with full bi-directional sync.

### System-Managed Policies

DockFlare automatically manages two core policies for consistency:

- **`public-default-bypass`**: Public access bypass policy
  - Non-deletable system policy
  - Created automatically during initialization
  - Cloudflare name: `DockFlare-Default-Public-Access-Bypass`
  - Decision: `bypass` with `everyone` include rule
  - Used by all services requiring public access with zone protection bypass
  - Prevents duplicate bypass policies in your Cloudflare dashboard

- **`authenticated-default`**: Default authentication policy
  - Non-deletable system policy
  - Created automatically during initialization
  - Cloudflare name: `DockFlare-Default-Authenticated-Access`
  - Decision: `allow` with one-time PIN + email restriction
  - Used for basic authenticated access scenarios

### Legacy Label Migration

DockFlare automatically migrates legacy labels to use system policies:

- `dockflare.access.policy=bypass` → Uses `public-default-bypass`
- `dockflare.access.group=bypass` → Uses `public-default-bypass`
- `dockflare.access.policy=authenticate` → Uses `authenticated-default`

Migration happens transparently during container processing and reconciliation. No manual intervention required.

### Zone Default Policies

Zone-level wildcard policies (`*.domain.com`) provide layered security through policy priority:

1. **Specific hostname policy** (e.g., `app.example.com`) - Highest priority
2. **Zone wildcard policy** (e.g., `*.example.com`) - Fallback
3. **No policy** = Public access (no Access App) - Default

This ensures forgotten or undocumented services are still protected by the zone-level policy, acting as a security safety net.

**Example:**
- Zone policy: `*.internal.company.com` → Requires company email authentication
- Specific service: `public-demo.internal.company.com` → Uses `public-default-bypass`
- Forgotten service: `test.internal.company.com` → Protected by zone policy (requires auth)
