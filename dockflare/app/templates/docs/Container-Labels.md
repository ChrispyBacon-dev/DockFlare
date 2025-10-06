# Container Labels Reference

DockFlare is configured primarily through Docker labels attached to your containers. This page provides a comprehensive reference for all supported labels.

## Basic Configuration

These labels control the fundamental routing and service definition for a container.

| Label | Description | Example |
| :--- | :--- | :--- |
| `dockflare.enable` | **Required.** The master switch. Must be set to `true` for DockFlare to manage the container. | `dockflare.enable=true` |
| `dockflare.hostname` | **Required.** The public-facing hostname for your service. | `dockflare.hostname=myservice.example.com` |
| `dockflare.service` | **Required.** The internal URL of the service that Cloudflare Tunnel should connect to. Can be `http`, `https`, `tcp`, `ssh`, `rdp`, `http_status:XXX`, or `bastion`. | `dockflare.service=http://my-app-container:8080` |
| `dockflare.path` | The URL path to route to this service. Useful for exposing multiple services on the same hostname. | `dockflare.path=/api` |
| `dockflare.zonename` | (Optional) Explicit Cloudflare zone (domain) where the DNS record should be created. If omitted, DockFlare now auto-detects the zone based on the hostname and only falls back to the configured default (`CF_ZONE_ID`) when auto-detect fails. | `dockflare.zonename=another-domain.com` |
| `dockflare.no_tls_verify` | If set to `true`, disables TLS certificate verification for the connection between `cloudflared` and your origin service. Useful for origins with self-signed certificates. | `dockflare.no_tls_verify=true` |
| `dockflare.originsrvname` | Sets a specific Server Name Indication (SNI) hostname for the TLS connection to the origin. This is also known as "Origin Server Name" in the Cloudflare dashboard. | `dockflare.originsrvname=internal.service.local` |
| `dockflare.httpHostHeader` | Overrides the `Host` header sent from `cloudflared` to your origin service. | `dockflare.httpHostHeader=custom-host.internal` |

> **Tip:** Starting with DockFlare v3.0, you can skip `dockflare.zonename` for most workloads. The master detects the correct Cloudflare zone by matching the hostname suffix and only falls back to the configured default zone when it cannot find a match. Provide the label when you intentionally want to place a record in a different zone.

---

## Access Policy Configuration

These labels allow you to dynamically create and manage Cloudflare Access applications to secure your services.

**Note:** It is highly recommended to use **Access Groups** (`dockflare.access.group`) for managing policies. DockFlare 3.0.3 synchronises every Access Group to a named reusable Cloudflare Access Policy, giving you one-to-many reuse and bi-directional edits. Using individual labels is best for one-off, unique configurations. If `dockflare.access.group` or `dockflare.access.groups` is used, all other `dockflare.access.*` labels are ignored.

### Important Changes in v3.0.3

#### System Default Bypass Policy

Starting in v3.0.3, when you use `dockflare.access.policy=bypass` or `dockflare.access.group=bypass`, your service will reference the system-managed `public-default-bypass` reusable policy instead of creating an inline policy. This keeps your Cloudflare dashboard clean.

- **Before v3.0.3:** Each bypass rule created a separate inline policy
- **v3.0.3+:** All bypass rules share one canonical `public-default-bypass` policy

#### Legacy Label Migration

DockFlare automatically migrates legacy bypass labels to use the centralized system policy:

- `dockflare.access.policy=bypass` → Uses `public-default-bypass` system policy
- `dockflare.access.group=bypass` → Uses `public-default-bypass` system policy

The migration happens transparently during container processing and reconciliation. Your containers will continue to work without any changes required.

#### Simplified Access Configuration

For complex access scenarios (email/domain authentication, IP whitelisting, etc.), it's now recommended to:

1. Create an Access Group on the **Access Policies** page
2. Reference it with `dockflare.access.group=your-group-id`

Quick-create options have been removed from the UI to encourage this best-practice workflow.

#### Zone Default Policy Label

The `dockflare.access.policy=default_tld` label still works and will inherit protection from your zone's `*.domain.com` wildcard policy. If no zone policy exists, the service will be public (no Access App).

**Recommendation:** Create zone default policies for all your domains in the UI for better security.

| Label | Description | Example |
| :--- | :--- | :--- |
| `dockflare.access.group` | The ID of a single, pre-configured Access Group to apply to this service. The ID can be found on the "Access Policies" page in the DockFlare UI. | `dockflare.access.group=internal-tools-policy` |
| `dockflare.access.groups` | A comma-separated list of Access Group IDs to apply. This allows you to layer multiple policies onto a single service. | `dockflare.access.groups=allow-team-a,allow-admins` |
| `dockflare.access.policy` | The primary policy type. Can be `bypass` (public), `authenticate` (requires login), or `default_tld` (inherits from a `*.domain.com` policy). If unset, the service will be public. Prefer Access Groups for reusable policies; these labels are for specialised overrides. | `dockflare.access.policy=authenticate` |
| `dockflare.access.name` | A custom name for the Cloudflare Access Application. Defaults to `DockFlare-{hostname}`. | `dockflare.access.name=My Web App Access` |
| `dockflare.access.session_duration` | The session duration for authenticated users (e.g., `24h`, `30m`). Defaults to `24h`. | `dockflare.access.session_duration=1h` |
| `dockflare.access.app_launcher_visible` | If `true`, makes the application visible in the Cloudflare Access App Launcher. | `dockflare.access.app_launcher_visible=true` |
| `dockflare.access.allowed_idps` | A comma-separated list of allowed Identity Provider (IdP) UUIDs. You can find these in your Cloudflare Zero Trust dashboard. | `dockflare.access.allowed_idps=uuid1,uuid2` |
| `dockflare.access.auto_redirect_to_identity` | If `true`, users will be immediately redirected to the IdP login page instead of the Cloudflare Access splash page. | `dockflare.access.auto_redirect_to_identity=true` |
| `dockflare.access.custom_rules` | A JSON string representing an array of Cloudflare Access Policy rules. This provides maximum flexibility for complex, one-off policies. | `dockflare.access.custom_rules='[{"email":{"email":"user@example.com"},"action":"allow"}]'` |

---

## Indexed Labels for Multiple Domains

DockFlare supports defining multiple hostnames for a single container using indexed labels. This is useful for exposing different ports or paths of the same service on different public hostnames.

To use indexed labels, prefix the label with an integer, starting from `0`.

*   An indexed hostname (`<index>.hostname`) is always required.
*   Other labels at the same index (e.g., `<index>.service`, `<index>.path`) will override the base (non-indexed) labels for that specific hostname.
*   If an indexed label is not provided, it will fall back to the value of the corresponding base label.

### Example

This example exposes two hostnames from a single container:
1.  `app.example.com` routes to the main web interface on port `80`.
2.  `api.example.com` routes to the API on port `3000` and is secured with a specific Access Group.

```yaml
services:
  my-multi-service:
    image: my-app
    labels:
      - "dockflare.enable=true"

      # --- Definition 0 ---
      - "dockflare.0.hostname=app.example.com"
      - "dockflare.0.service=http://my-multi-service:80"

      # --- Definition 1 ---
      - "dockflare.1.hostname=api.example.com"
      - "dockflare.1.service=http://my-multi-service:3000"
      - "dockflare.1.access.group=api-access-policy"
```
