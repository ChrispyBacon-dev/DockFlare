![DockFlareBanner](images/bannertr.png)
[![Maintenance](https://img.shields.io/badge/Maintained%3F-yes-green.svg)](https://github.com/ChrispyBacon-dev/baconflip)
[![OS](https://img.shields.io/badge/os-linux%20%7C%20windows%20%7C%20macos-brightgreen)]()
[![CPU Architectures](https://img.shields.io/badge/CPU-x86_64%20%7C%20arm64-brightgreen)](https://en.wikipedia.org/wiki/Central_processing_unit)
[![Generic badge](https://img.shields.io/badge/Release-1.7-blue.svg)](https://shields.io/)
[![Docker Pulls](https://img.shields.io/docker/pulls/alplat/dockflare)](https://hub.docker.com/r/alplat/dockflare)
[![made-with-python](https://img.shields.io/badge/Made%20with-Python-1f425f.svg)](https://www.python.org/)
[![GitHub issues](https://img.shields.io/github/issues/ChrispyBacon-dev/dockflare)](https://github.com/ChrispyBacon-dev/dockflare/issues)
[![GitHub last commit](https://img.shields.io/github/last-commit/ChrispyBacon-dev/dockflare)](https://github.com/ChrispyBacon-dev/dockflare/commits/stable)
[![GitHub commit activity](https://img.shields.io/github/commit-activity/m/ChrispyBacon-dev/dockflare)](https://github.com/ChrispyBacon-dev/dockflare/commits/stable)

DockFlare streamlines Cloudflare Tunnel and Zero Trust Access policy management by leveraging Docker labels for automated configuration and a comprehensive web UI for manual service definition and policy overrides for any rule. It simplifies secure public exposure for both Dockerized and non-Dockerized applications, minimizing direct Cloudflare interaction. DockFlare acts as a dynamic, self-hosted ingress controller, offering persistent, UI-driven control over Access Policies, effectively centralizing your basic access management.

## Key Features

-   **Unified Cloudflare Tunnel Management**:
    -   Automates Tunnel creation/use & `cloudflared` agent lifecycle (optional internal deployment or external).
-   **Dynamic Ingress via Docker Labels**:
    -   Auto-configures Tunnel ingress & DNS from Docker labels (e.g., `cloudflare.tunnel.hostname`, `service`) by monitoring container events.
-   **Manual Ingress Rule Management (New!)**:
    -   Add & manage public hostnames for non-Docker services (e.g., router, NAS) via Web UI; DockFlare handles Tunnel rules & DNS.
-   **Versatile Access Policy Control (Docker & Manual)**:
    -   Define Cloudflare Access Policies (e.g., `bypass`, `authenticate`, custom JSON) via Docker labels; auto-manages Access Applications.
    -   Web UI to manage/override policies for *any* rule; UI changes persist, override labels, with revert option & clear indicators.
-   **Multi-Hostname & Multi-Zone**:
    -   Supports multiple hostnames (unique targets, zones, policies) per Docker container (indexed labels) or manual rule.
-   **State Persistence & Graceful Deletion**:
    -   Configurable grace period for Docker rule cleanup; persists all managed rules, Access App IDs, & UI overrides in `state.json`.
-   **Intelligent Reconciliation**:
    *   Continuously syncs Docker, manual entries, & saved state (respecting UI overrides) with Cloudflare (Tunnel, DNS, Access Apps); shows UI progress.
-   **Comprehensive Web UI (DaisyUI)**:
    -   **Dashboard**: Tunnel/agent status & controls.
    -   **Unified Rule List**: View/manage all rules (Docker & manual) with status, target, Access Policy (Cloudflare links, UI override badges), & delete options.
    -   **Easy Manual Entry**: Add non-Docker services via UI.
    -   **Account Tools**: View account tunnels/DNS.
    -   **Real-time Logs & Themes**: SSE activity logs & multiple UI themes.
-   **Secure & Robust**:
    -   Content Security Policy (CSP), API retries, and error reporting.

[Learn more on the GitHub Wiki](https://github.com/ChrispyBacon-dev/DockFlare/wiki)

![Web ui example](images/status_web.png)

## How It Works

DockFlare listens for Docker container events. 
- **Label-First for Initial Setup**: By labeling your containers, DockFlare initially configures Cloudflare Tunnel ingress rules, DNS records, and associated Cloudflare Zero Trust Access Applications.
- **UI for Dynamic Overrides**: The Web UI allows you to dynamically change Access Policies for individual services. These UI changes take precedence over container labels and are persistent.
- **Revert Option**: You can always revert a UI-managed Access Policy back to be controlled by the container's labels via the Web UI.

### Example Workflow

1.  **Start DockFlare**: Run the DockFlare container with the required environment variables.
2.  **Label Your Containers**: Add labels to your Docker containers to define their public hostname, service target, and *initial* desired Access Policy.
3.  **Automatic Configuration**: DockFlare detects labeled containers and:
    - Updates the Cloudflare Tunnel configuration.
    - Creates/updates DNS CNAME records.
    - Creates/updates Cloudflare Access Applications based on `access.*` labels (if not already UI-overridden).
4.  **Manage Access Policies via UI (Optional)**: Modify Access Policies directly through the DockFlare web interface. These changes are persistent and override labels. Click "Revert to Labels" to restore label-based management.
5.  **Graceful Deletion**: When a container stops, DockFlare schedules its ingress rule and any DockFlare-managed Access Application for deletion after a configurable grace period.

## Getting Started

### Prerequisites

- Docker: [Install Docker](https://docs.docker.com/engine/install/)
- Docker Compose: [Install Docker Compose](https://docs.docker.com/compose/install/)
- Cloudflare Account with:
  - API Token with Account:Cloudflare Tunnel:Edit, Account:Account Settings:Read, Account:Access: Apps and Policies:Edit, Zone:Zone:Read, Zone:DNS:Edit
  ![Cloudflare API](images/cf.png)

  (Account Settings Read is no needed but planned for upcoming new feature)
  - Account ID (found in Cloudflare Dashboard → Overview)
  - Zone ID (found in Cloudflare Dashboard → Overview)
  
### Quick Start (Using Docker Compose)

1. **Create `docker-compose.yml`**:

   ```yaml
   version: '3.8'
   services:
     dockflare:
       image: alplat/dockflare:stable
       container_name: dockflare
       restart: unless-stopped
       ports:
         - "5000:5000"  # Web UI port
       env_file:
         - .env  # Load environment variables from .env file
       environment:
         - STATE_FILE_PATH=/app/data/state.json
         - TZ=Europe/Zurich  # Set your timezone here  
       volumes:
         - /var/run/docker.sock:/var/run/docker.sock:ro  # Required to monitor Docker events
         - dockflare_data:/app/data  # Persistent storage for state
       networks:
         - cloudflare-net  # Network for communication with cloudflared agent
       labels: # Optional keep in mind to set access policy
         - cloudflare.tunnel.enable=true
         - cloudflare.tunnel.hostname=dockflare.yourdomain.tld # update your domain 
         - cloudflare.tunnel.service=http://dockflare:5000 
   volumes:
     dockflare_data:
   networks:
     cloudflare-net:
      name: cloudflare-net
   ```

2. **Create `.env` File**:
   ```dotenv
   # Cloudflare API Token (REQUIRED)
   CF_API_TOKEN=your_cloudflare_api_token
   # Cloudflare Account ID (REQUIRED) - dash.cloudflare.com/ACCOUNT_ID
   CF_ACCOUNT_ID=your_cloudflare_account_id
   # Cloudflare Zone ID (REQUIRED)
   CF_ZONE_ID=your_cloudflare_zone_id
   # Tunnel Name (REQUIRED only when NOT using external cloudflared)
   TUNNEL_NAME=DockFlare
   # Docker Network Name (internal cloudflared mode)
   CLOUDFLARED_NETWORK_NAME=cloudflare-net
   # Label Prefix for Docker Containers
   LABEL_PREFIX=cloudflare.tunnel
   # Grace Period for Rule Deletion (seconds, default: 1h)
   GRACE_PERIOD_SECONDS=6000
   # Cleanup Interval (seconds)
   CLEANUP_INTERVAL_SECONDS=300
   # Agent Status Update Interval (seconds)
   AGENT_STATUS_UPDATE_INTERVAL_SECONDS=10
   # Scan All Docker Networks (default: false)
   SCAN_ALL_NETWORKS=false
   # Max Concurrent DNS Operations (default: 3)
   MAX_CONCURRENT_DNS_OPS=3
   # Reconciliation Batch Size (default: 3)
   RECONCILIATION_BATCH_SIZE=3
   # Trusted Proxies (IPs/CIDR ranges)
   # TRUSTED_PROXIES=172.16.0.0/12,192.168.0.0/16
   # Default TLS Verification Setting (skip verification) (default: false)
   DEFAULT_NO_TLS_VERIFY=false
   STATE_FILE_PATH=/app/data/state.json

3. **Run DockFlare**:

   ```bash
   docker compose up -d
   ```

4. **Access the Web UI**: Open `http://localhost:5000` in your browser.

### Labeling Containers

DockFlare supports two approaches for labeling containers:

#### 1. Standard Labels (Single Domain)

To expose a single service through DockFlare, add the following labels to your container:

```yaml
services:
  my-service:
    image: nginx:latest
    labels:
      # Enable DockFlare management for this container
      cloudflare.tunnel.enable: "true"
      
      # The public hostname to expose (must be a valid domain you control)
      cloudflare.tunnel.hostname: "my-service.example.com"
      
      # The internal service address (protocol://host:port)
      cloudflare.tunnel.service: "http://my-service:80"
      
      # Optional: Specify a different zone for this hostname
      # cloudflare.tunnel.zonename: "example.com"
      
      # Optional: Disable TLS verification for this service
      # cloudflare.tunnel.no_tls_verify: "true"
    networks:
      - cloudflare-net  # Must be in a network that DockFlare can reach     
```

#### 2. Indexed Labels (Multiple Domains)

To expose multiple domains from a single container, use indexed labels to define each configuration:

```yaml
services:
  multi-domain-service:
    image: nginx:latest
    labels:
      # Enable DockFlare for this container
      - "cloudflare.tunnel.enable=true"
      
      # First hostname (using indexed notation)
      - "cloudflare.tunnel.0.hostname=my-service.example.com"
      - "cloudflare.tunnel.0.service=http://my-service:80"
      - "cloudflare.tunnel.0.no_tls_verify=true"
      
      # Second hostname (using indexed notation)
      - "cloudflare.tunnel.1.hostname=my-service2.example.com"
      - "cloudflare.tunnel.1.service=http://my-service:80"
      - "cloudflare.tunnel.1.no_tls_verify=true"
      
      # Third hostname with a different zone
      - "cloudflare.tunnel.2.hostname=my-service.otherdomain.com"
      - "cloudflare.tunnel.2.service=http://my-service:80"
      - "cloudflare.tunnel.2.no_tls_verify=true"
      - "cloudflare.tunnel.2.zonename=otherdomain.com"
    networks:
      - cloudflare-net
```

With indexed labels, each domain can have:

Different target services (useful for exposing different ports or paths)
Different TLS verification settings
Different zone names for multi-domain management
This feature works with both internal and external cloudflared modes, making it perfect for services that need to be accessible across multiple domains or subdomains.

> **Note**: Index numbers must be sequential starting from 0 (0, 1, 2, etc.). Any gap in the sequence will cause DockFlare to stop processing further indices.

### Finding Your Tunnel ID

When using the external cloudflared mode, you'll need to provide the Tunnel ID. Here's how to find it:

1. Log in to your [Cloudflare Dashboard](https://dash.cloudflare.com)
2. Navigate to **Access** → **Tunnels** in the left sidebar
3. Find your tunnel in the list and click on it
4. The Tunnel ID is displayed in two places:
   - In the URL of the page: `https://dash.cloudflare.com/[account-id]/access/tunnels/view/[tunnel-id]`
   - In the **Overview** tab under "Tunnel ID"
5. Copy this ID and set it as your `EXTERNAL_TUNNEL_ID` in the `.env` file

Example Tunnel ID format: `6ff42ae2-765d-4adf-befc-ca51f8e4e688`

### Switching Between Internal and External Cloudflared Modes

If you want to switch from using DockFlare's built-in cloudflared container to an external cloudflared instance, you'll need to perform several cleanup steps to ensure a smooth transition:

1. **Stop the DockFlare container** first:
   ```bash
   docker stop dockflare
   ```

2. **Remove the existing cloudflared agent container** managed by DockFlare:
   ```bash
   docker rm -f cloudflared-agent-your_tunnel_name
   ```

3. **Clean up DNS records in Cloudflare dashboard**:
   - Navigate to Cloudflare Dashboard → DNS
   - Find and delete the CNAME records created for your services
   - These typically have names matching your container hostnames and point to `{tunnel-id}.cfargotunnel.com`

4. **Delete the tunnel in Cloudflare dashboard** (if you're creating a new external tunnel):
   - Navigate to Cloudflare Dashboard → Access → Tunnels
   - Find the tunnel created by DockFlare
   - Click the three dots menu → Delete

5. **Reset the state file** to ensure clean configuration:
   ```bash
   # If using Docker volumes
   docker volume rm dockflare_data
   # Or if mounted as a file
   rm /path/to/your/state.json
   ```

6. **Set up your external cloudflared instance** following Cloudflare's documentation:
   - Create a new tunnel or use an existing one
   - Make sure to note the Tunnel ID
   - Configure and run the cloudflared daemon

7. **Update your .env file** with the external configuration:
   ```dotenv
   USE_EXTERNAL_CLOUDFLARED=true
   EXTERNAL_TUNNEL_ID=your_external_tunnel_id
   ```

8. **Restart DockFlare** with the new configuration:
   ```bash
   docker start dockflare
   # Or if you removed the volume, you may need to recreate the container
   docker compose up -d
   ```

9. **Verify container discovery** after restart:
   - Check the Web UI to ensure your containers are detected
   - Verify that DNS records are created for your services
   - Test that your services are accessible through the tunnel

After the switch, DockFlare will:
- Discover containers with the appropriate labels
- Create new DNS records pointing to your external tunnel
- Update the ingress configuration for your external tunnel
- Start with a fresh state based on your running containers

> **Note**: During this transition, your services may experience brief downtime as DNS records are deleted and recreated. The DNS propagation might take some time depending on TTL settings.

> **Important**: When switching to external mode, the tunnel name in your .env file is no longer used, but you still need to specify the correct `EXTERNAL_TUNNEL_ID`.

## Advanced Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `CF_API_TOKEN` | Cloudflare API token | (Required) |
| `CF_ACCOUNT_ID` | Cloudflare account ID | (Required) |
| `CF_ZONE_ID` | Default/fallback Cloudflare zone ID | (Required unless all containers use `zonename` label) |
| `TUNNEL_NAME` | Name for the Cloudflare tunnel | dockflared-tunnel (Required unless using external tunnel) |
| `GRACE_PERIOD_SECONDS` | Time before removing rules after container stops | 28800 (8 hours) |
| `CLEANUP_INTERVAL_SECONDS` | Interval for checking expired rules | 300 (5 minutes) |
| `LABEL_PREFIX` | Prefix for Docker labels | cloudflare.tunnel |
| `USE_EXTERNAL_CLOUDFLARED` | Use an existing cloudflared agent | false |
| `EXTERNAL_TUNNEL_ID` | Tunnel ID for external cloudflared mode | (Required if `USE_EXTERNAL_CLOUDFLARED=true`) |
| `SCAN_ALL_NETWORKS` | Scan containers across all Docker networks | false |
| `CLOUDFLARED_NETWORK_NAME` | Docker network for cloudflared agent | cloudflare-net |
| `STATE_FILE_PATH` | Path for state persistence | /app/data/state.json |

### Container Labels

| Label | Description | Required | Example |
|-------|-------------|----------|---------|
| `{prefix}.enable` | Enable DockFlare for this container | Yes | `"true"` |
| `{prefix}.hostname` | Public hostname to expose | Yes | `"app.example.com"` |
| `{prefix}.service` | Internal service address | Yes | `"http://app:80"` |
| `{prefix}.zonename` | Zone name for this hostname | No | `"example.com"` |
| `{prefix}.no_tls_verify` | Disable TLS verification | No | `"true"` |

### Access Policy Labels (Zero Trust)

These labels define the initial Cloudflare Access Policy for the exposed `hostname`. **Note:** These label-defined policies can be overridden by changes made in the DockFlare [Web UI](UsingtheWebUI.md). If a UI override is active, these labels will not be re-applied unless the policy is "Reverted to Labels" via the UI.

| Label                                   | Description                                                                                                                                                                                             | Default | Example                                                  |
| :-------------------------------------- | :------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | :------ | :------------------------------------------------------- |
| `{prefix}.access.policy`                | Defines the type of Access Policy. Common values: `bypass` (public), `authenticate` (requires login via configured IdPs), `default_tld` (inherits from `*.yourdomain.com` policy, no app created for this specific hostname). | (None)  | `cloudflare.tunnel.access.policy="authenticate"`       |
| `{prefix}.access.name`                  | Custom name for the Cloudflare Access Application.                                                                                                                                                      | `DockFlare-{hostname}` | `cloudflare.tunnel.access.name="My Web App Access"`     |
| `{prefix}.access.session_duration`      | Session duration for the Access Application (e.g., `24h`, `30m`).                                                                                                                                       | `24h`   | `cloudflare.tunnel.access.session_duration="1h"`       |
| `{prefix}.access.app_launcher_visible`  | If `"true"`, the application will be visible in the Cloudflare App Launcher.                                                                                                                            | `false` | `cloudflare.tunnel.access.app_launcher_visible="true"` |
| `{prefix}.access.allowed_idps`          | Comma-separated list of allowed Identity Provider (IdP) UUIDs. If `access.policy="authenticate"` and this is not set, it typically allows any configured IdP for the account.                            | (Account Default) | `cloudflare.tunnel.access.allowed_idps="<IdP_UUID_1>,<IdP_UUID_2>"` |
| `{prefix}.access.auto_redirect_to_identity` | If `"true"`, automatically redirects to the identity provider login page.                                                                                                                               | `false` | `cloudflare.tunnel.access.auto_redirect_to_identity="true"` |
| `{prefix}.access.custom_rules`          | A JSON string representing an array of Cloudflare Access Policy rules. Overrides `access.policy` if set to `authenticate` or `bypass` for policy decision. See [Cloudflare Access Policy Docs](https://developers.cloudflare.com/api/operations/access-policies-create-an-access-policy) for schema. | (None)  | `cloudflare.tunnel.access.custom_rules='[{"email":{"email":"user@example.com"},"action":"allow"}]'` |

**Example of Access Policy Labels:**

```yaml
labels:
  cloudflare.tunnel.enable: "true"
  cloudflare.tunnel.hostname: "secure-app.example.com"
  cloudflare.tunnel.service: "http://my-secure-app:8080"
  cloudflare.tunnel.access.policy: "authenticate"
  cloudflare.tunnel.access.session_duration: "8h"
  cloudflare.tunnel.access.allowed_idps: "YOUR_GITHUB_IDP_UUID_HERE" 
  # This creates an Access Application named "DockFlare-secure-app.example.com"
  # that requires authentication via the specified GitHub IdP with an 8-hour session.
```

### External Cloudflared Mode (DANGER ZONE)

DockFlare can work with an existing `cloudflared` container. This is useful if you're already using cloudflared for other services or prefer to manage it separately. To enable this mode:

1. Set `USE_EXTERNAL_CLOUDFLARED=true` in your `.env` file.
2. Provide the external tunnel ID using `EXTERNAL_TUNNEL_ID`.

In this mode, DockFlare will only manage DNS records and ingress rules, but not the cloudflared agent itself.

```dotenv
USE_EXTERNAL_CLOUDFLARED=true
EXTERNAL_TUNNEL_ID=your-tunnel-id-from-cloudflare
```
Update on version 1.7
The `update_cloudflare_config` function now takes a more authoritative stance: for the DockFlare-managed tunnel, any non-wildcard, non-catch-all ingress rule found on Cloudflare that is *not* present in DockFlare's `managed_rules` (either from Docker labels or manual UI entries) will be removed by DockFlare. This ensures the tunnel configuration accurately reflects DockFlare's intended state. True external wildcards and the API's catch-all rule are still preserved.

This means as well that DNS records that are not present in the DockFlare rules will be removed from your DNS Zone. External Mode is not recommended only if you know what to do and are for Edge cases. 

### Real-time Log Streaming

DockFlare provides real-time logs using Server-Sent Events (SSE). Open the "Real-time Activity Logs" section in the Web UI to view logs as they happen. This feature is especially useful for monitoring container events and configuration changes.

### DNS Zone Management

DockFlare supports hosting services across multiple Cloudflare zones (domains). There are two ways to specify which zone a hostname belongs to:

1. **Container-specific zone using labels**: Use the `cloudflare.tunnel.zonename` label to specify the zone name for a specific hostname. DockFlare will look up the zone ID automatically.

2. **Default zone using environment variable**: Set the `CF_ZONE_ID` environment variable as a fallback for any hostname that doesn't specify a `zonename` label.

For multi-domain setups, you have two options:
- **Option 1**: Set `CF_ZONE_ID` to your primary domain's Zone ID, and use `zonename` labels only for hostnames in other zones
- **Option 2**: Always specify `zonename` labels for all hostnames, making the `CF_ZONE_ID` environment variable optional

> **Note**: When using wildcard domains like `*.example.com`, ensure you're using the correct zone, either via the `zonename` label or the default `CF_ZONE_ID`.

```yaml
services:
  my-service:
    # ...other configuration...
    labels:
      cloudflare.tunnel.0.enable: "true"
      cloudflare.tunnel.0.hostname: "app.customdomain.com"
      cloudflare.tunnel.0.service: "http://my-service:80"
      cloudflare.tunnel.0.zonename: "customdomain.com"  # Explicitly defines the zone
```

#### 3. Wildcard Domain Support

DockFlare supports wildcard domains for routing all subdomains through your tunnel:

```yaml
services:
  wildcard-service:
    image: nginx:latest
    labels:
      - "cloudflare.tunnel.enable=true"
      # Wildcard domain - routes all subdomains
      - "cloudflare.tunnel.hostname=*.example.com"
      - "cloudflare.tunnel.service=https://my-service:443"
      - "cloudflare.tunnel.no_tls_verify=true"
    networks:
      - cloudflare-net
```

This configuration will route all subdomains of example.com through your tunnel to the specified service. This is useful for:
- Multi-tenant applications where each tenant gets their own subdomain
- Development environments with dynamic subdomains
- Catch-all routing for a domain

> **Note**: Specific subdomain rules take precedence over wildcard rules. For example, if you have both `*.example.com` and `specific.example.com` configured, requests to `specific.example.com` will be routed according to its specific rule.

### Performance Tuning

DockFlare includes several features to optimize performance and prevent rate limiting:

1. **Concurrent DNS Operation Limiting**: 
   - Controls how many simultaneous DNS operations can run
   - Prevents Cloudflare API rate limiting during large reconciliations
   - Configurable via `MAX_CONCURRENT_DNS_OPS` (default: 3)

2. **Batched DNS Processing**:
   - Processes DNS records in small batches during reconciliation
   - Shows real-time progress feedback in the web UI
   - Configurable via `RECONCILIATION_BATCH_SIZE` (default: 3)

3. **Asynchronous Initialization**:
   - Web UI is immediately available while initialization continues
   - Progress indicators show current status of initialization and reconciliation

These optimizations are particularly helpful when managing tunnels with many domains or when running on systems with limited resources.

## Troubleshooting

### Common Issues

- **Log Stream Not Working**: Ensure your browser supports Server-Sent Events (SSE). Try a different browser or check for network filtering.
- **Reverse Proxy Issues**: If you're using a reverse proxy in front of DockFlare's Web UI, make sure it's configured to properly handle SSE connections and WebSocket connections.
- **Container Not Being Detected**: Verify that:
  - Your container has the right labels
  - The container is in a network DockFlare can access (use `SCAN_ALL_NETWORKS=true` if needed)
  - The hostname format is valid (must be a proper domain name)
  - The service format is valid (must include protocol and host:port)

### Debugging

- Check the logs in the Web UI or the container logs using:

  ```bash
  docker logs dockflare
  ```

- Verify Cloudflare API token permissions: Requires Zone:DNS:Edit and Account:Cloudflare Tunnel:Edit

- If a container stops responding to changes, try forcing deletion of the rule via the Web UI and then restart the container.

### Health Checks

- **DockFlare Health**: Access `http://localhost:5000/ping` for basic health information
- **Cloudflare Connectivity**: Access `http://localhost:5000/cloudflare-ping` through your tunnel to verify Cloudflare connection details

## Contributing

Contributions are welcome! Please open an issue or submit a pull request on GitHub.

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

DockFlare is licensed under the GNU General Public License version 3 License. See [LICENSE.MD](https://github.com/ChrispyBacon-dev/DockFlare?tab=License-1-ov-file) for details.
