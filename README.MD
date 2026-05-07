<p align="center">
  <a href="https://dockflare.app" title="Now you're thinking with tunnels">
    <picture>
      <source media="(prefers-color-scheme: dark)" srcset="images/logo-files/logo-dark.svg">
      <source media="(prefers-color-scheme: light)" srcset="images/logo-files/logo-light.svg">
      <img src="images/logo-files/logo-light.svg" width="500px" alt="DockFlare Logo" />
    </picture>
  </a>
</p>

<h1 align="center">Automate Cloudflare Tunnels with Docker Labels</h1>

<p align="center">
  <em>Go from container to publicly-secured URL in seconds. No manual Cloudflare dashboard configuration required.</em>
</p>

<p align="center">
<a href="https://github.com/ChrispyBacon-dev/DockFlare/stargazers">
  <img src="https://img.shields.io/github/stars/ChrispyBacon-dev/DockFlare?style=for-the-badge" alt="Stars">
</a>
  <a href="https://github.com/ChrispyBacon-dev/DockFlare/releases"><img src="https://img.shields.io/badge/Release-v3.1.2-blue.svg?style=for-the-badge" alt="Release"></a>
  <a href="https://hub.docker.com/r/alplat/dockflare"><img src="https://img.shields.io/docker/pulls/alplat/dockflare?style=for-the-badge" alt="Docker Pulls"></a>
  <a href="https://www.python.org/"><img src="https://img.shields.io/badge/Made%20with-Python-1f425f.svg?style=for-the-badge" alt="Python"></a>
  <a href="https://github.com/ChrispyBacon-dev/DockFlare/blob/main/LICENSE.MD"><img src="https://img.shields.io/badge/License-GPL--3.0-blue.svg?style=for-the-badge" alt="License"></a>
  <a href="#"><img src="https://img.shields.io/badge/Swiss_Made-FFFFFF?style=for-the-badge&labelColor=FF0000&logo=data:image/svg%2bxml;base64,PHN2ZyB2ZXJzaW9uPSIxIiB3aWR0aD0iNTEyIiBoZWlnaHQ9IjUxMiIgdmlld0JveD0iMCAwIDMyIDMyIiB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciPgogIDxyZWN0IHdpZHRoPSIzMiIgaGVpZHRoPSIzMiIgZmlsbD0idHJhbnNwYXJlbnQiLz4KICA8cGF0aCBkPSJtMTMgNmg2djdoN3Y2aC03djdoLTZ2LTdoLTd2LTZoN3oiIGZpbGw9IiNmZmYiLz4KPC9zdmc+" alt="Swiss Made"></a>
</p>

<p align="center">
  <a href="https://dockflare.app">Website</a> ·
  <a href="https://dockflare.app/docs">Documentation</a> ·
  <a href="https://github.com/ChrispyBacon-dev/DockFlare/issues">Report a Bug</a> ·
  <a href="https://github.com/sponsors/ChrispyBacon-dev">Sponsor</a>
</p>

---

## Introduction

DockFlare is a self-hosted ingress and access-control plane for Cloudflare Tunnel environments. It continuously translates your desired state into Cloudflare configuration by combining Docker labels, manual rules from the web UI, and optional remote agents.

It was built to remove repetitive dashboard work from fast-changing self-hosted environments. Instead of manually updating DNS records, tunnel ingress rules, and Access applications, you define intent once and DockFlare reconciles it.

The result is a set-it-and-forget-it workflow with a fully localized native experience: less operational drift, more reliable service exposure, and one place to manage routing and access decisions.

## Core Capabilities

- **Automatic service discovery** from Docker labels.
- **Sovereign Email Suite**: A fully self-hosted email system using Cloudflare Email Routing as a stateless delivery layer with local data sovereignty.
- **Multi-Domain Email Support**: Manage inbound and outbound email for an unlimited number of domains simultaneously.
- **PWA-Ready Webmail**: Modern, installable Vue 3 webmail client with offline support and desktop/mobile push notifications.
- **Automated Infrastructure Provisioning**: One-click setup for Cloudflare Workers, R2 buckets, and Email Routing.
- **Advanced DNS & DKIM Management**: Automatic zone-aware record placement with authoritative DKIM key handling.
- **Native Multi-Language Support** (13 languages) for the Web UI and Help Center.
- **Manual Ingress Rule Management** for non-Docker workloads.
- **Cloudflare Tunnel Ingress Orchestration**, including advanced origin options.
- **Access Group & Reusable Policy Management** with application assignment.
- **Cloudflare Access Application Lifecycle Management**.
- **Multi-Host Operation** through a master and lightweight agents.
- **Secure Agent Communication** via Cloudflare Zero Trust service tokens.
- **Backup & Restore** of encrypted configuration, runtime state, and email data.

## Architecture Overview

Detailed architecture guide: [https://dockflare.app/architecture](https://dockflare.app/architecture)

| Component | Purpose |
| --- | --- |
| DockFlare Master | Web UI, encrypted config/state, reconciliation, Cloudflare API orchestration |
| DockFlare Mail Manager | Sovereign email backend, SQLite storage, R2 integration, and webhook handling |
| DockFlare Webmail | PWA-ready mail client with push notification support |
| Redis | Shared cache, coordination, and pub/sub signaling |
| DockFlare Agent | Remote host watcher and command executor for distributed deployments |
| cloudflared | Tunnel connector runtime managed per deployment mode |
| Cloudflare API | Source of truth for Tunnel, DNS, Email, and Access resources |

### Reconciliation Flow

1. DockFlare collects desired state from labels, manual rules, and agent-reported containers.
2. It computes deltas against persisted state and Cloudflare state.
3. It applies updates for ingress, DNS, and Access resources.
4. It updates local runtime state and keeps `cloudflared` aligned.

## Getting Started

### One-Liner Install

```bash
bash <(curl -fsSL https://dockflare.app/install.sh)
```

The script will guide you through:
1. Choosing an install directory (default: `~/dockflare/`).
2. Choosing a local UI port (default: `5000`).
3. Optionally configuring a Cloudflare Tunnel for DockFlare itself.
4. Optionally enabling the Email profile (dockflare-mail-manager + dockflare-webmail).

For full setup documentation, use the project docs site:

- [Quick Start Guide](https://dockflare.app/docs)
- [Container Label Reference](https://dockflare.app/docs/container-labels)
- [Advanced DNS and Zone Management](https://dockflare.app/docs/managing-dns-zones)
- [Multi-Server Agent Setup](https://dockflare.app/docs/multi-server-agent)

### Prerequisites

- Docker and Docker Compose.
- A Redis instance (the quick-start stack below includes one).
- A Cloudflare account.
- Cloudflare Account ID.
- Cloudflare Zone ID for your primary domain.
- Cloudflare API token with these permissions:
    * `Account:Cloudflare Tunnel:Write`
    * `Account:Account Settings:Read`
    * `Account:Access: Apps and Policies:Write`
    * `Account:Access: Organizations, Identity Providers, and Groups:Write`
    * `Account:Access: Service Tokens:Write`
    * `Zone:Zone:Read`
    * `Zone:DNS:Write`

    **For optional DockFlare Email features, add these additional permissions:**
    * `Workers Scripts:Write`
    * `Workers KV Storage:Write`
    * `Workers R2 Storage:Write`
    * `Email Routing Addresses:Write`
    * `Email Routing Rules:Write`


![Cloudflare API Permissions](images/cf.png)

<details>
<summary>Quick Start Docker Compose</summary>

Before first launch, create the shared network once:

```bash
docker network create cloudflare-net
```

1. Create `docker-compose.yml`:

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

2. Start DockFlare:

```bash
docker compose up -d
```

The Email Suite is an optional, opt-in feature and will not start by default. To include email services, add the `email` profile:

```bash
docker compose --profile email up -d
```

Email setup and provisioning guide: [Email Overview](https://github.com/ChrispyBacon-dev/DockFlare/blob/stable/dockflare/app/templates/docs/en/Email-Overview.md)

3. Open `http://your-server-ip:5000` and complete the setup wizard.

If you are migrating from older environment-based setups, DockFlare can import existing values during onboarding.

</details>

## Configuration Modes

### Docker Label Mode

Use container labels to declare hostname, service target, and access behavior. DockFlare observes lifecycle events and reconciles records and ingress rules automatically.

Detailed label reference: [https://dockflare.app/docs/container-labels](https://dockflare.app/docs/container-labels)

### Manual Rule Mode

Create and edit routes directly in the UI for static hosts, VMs, appliances, or external services. Manual rules support HTTP/HTTPS advanced origin options and are persisted in DockFlare state.

### Hybrid Mode

Use labels for most workloads while managing exceptions in UI. DockFlare merges both sources into one reconciliation model.

### Agent Mode (Multi-Server)

Run a central master with agents on remote Docker hosts. Agents stream host-local container events and execute commands while the master owns policy and Cloudflare configuration decisions.

Multi-agent setup guide: [https://dockflare.app/docs/multi-server-agent](https://dockflare.app/docs/multi-server-agent)

## Access Control Model

DockFlare uses Access Groups as the primary abstraction for reusable access intent.

- One Access Group can be attached to multiple services.
- Groups sync to reusable Cloudflare Access policies.
- Services map to Access applications using consistent naming and update logic.
- Public and authenticated patterns are supported through policy decisions.
- Zone-level defaults can be used to protect wildcard domains and reduce accidental exposure.

For one-off services, individual `dockflare.access.*` labels are still supported.

## Example Labels

```yaml
services:
  picoshare:
    image: mtlynch/picoshare
    labels:
      - "dockflare.enable=true"
      - "dockflare.hostname=files.example.com"
      - "dockflare.service=http://picoshare:8080"
      - "dockflare.access.group=nas-family"
```

```yaml
services:
  internal-tool:
    image: nginx:latest
    labels:
      - "dockflare.enable=true"
      - "dockflare.hostname=tool.example.com"
      - "dockflare.service=http://internal-tool:80"
      - "dockflare.access.policy=authenticate"
      - "dockflare.access.email=admin@example.com,@example.com"
```

## Reliability and Drift Management

- DockFlare reconciliation is designed to be idempotent.
- Runtime and configuration state are persisted in encrypted files.
- Manual rule options are preserved and re-applied across restarts.
- Optional unmanaged-ingress-field preservation can keep Cloudflare-side values that DockFlare does not explicitly model.
- Backup and restore enable rapid recovery of full control-plane state.

## Security Model

- Supports web authentication with local credentials and OAuth providers.
- Uses scoped Cloudflare API tokens.
- Encourages Docker socket proxy for least-privilege Docker API exposure.
- Runs containers as non-root (`UID/GID 65532`) in the reference setup.
- Supports agent API key lifecycle controls and enrollment flow.
- Optional Cloudflare Zero Trust service token authentication for all agent traffic, removing the need for a private network or VPN between master and agents.

## Operations and Day-2 Tasks

Common workflows handled in UI:

- Add, edit, and remove manual routes.
- Assign or change Access Groups on services.
- View service status and reconciliation state.
- Rotate or revoke agent API keys.
- Trigger agent tunnel actions.
- Export and restore backups.

## Troubleshooting Pointers

- Verify Cloudflare token scopes first when API calls fail.
- Confirm domain-to-zone mapping when records do not appear.
- Validate service URL format (`http://` or `https://`) for manual rules.
- Check agent heartbeat and enrollment status for remote hosts.
- Confirm Docker socket proxy permissions if container discovery fails.

Additional troubleshooting references:

- [Common Issues](dockflare/app/templates/docs/Common-Issues.md)
- [Container Labels](dockflare/app/templates/docs/Container-Labels.md)
- [Multi-Server Agent](dockflare/app/templates/docs/Multi-Server-Agent.md)

## Development

- Build and run locally:

```bash
docker compose build --no-cache
docker compose up -d
```

- Basic health checks:

```bash
curl http://localhost:5000/ping
curl http://localhost:5000/api/v2/overview
```

## Documentation Map

*(Available in 8 languages directly within the DockFlare UI or online)*

- Product docs: [https://dockflare.app/docs](https://dockflare.app/docs)
- Source docs in repository:
  - [Multi-Server Agent Guide](dockflare/app/templates/docs/Multi-Server-Agent.md)
  - [Using the Web UI](dockflare/app/templates/docs/Using-the-Web-UI.md)
  - [Managing DNS Zones](dockflare/app/templates/docs/Managing-DNS-Zones.md)
  - [Identity Providers](dockflare/app/templates/docs/Identity-Providers.md)

## Changelog

Release notes are maintained in [CHANGELOG.md](CHANGELOG.md).
ailable in 8 languages directly within the DockFlare UI or online)*

- Product docs: [https://dockflare.app/docs](https://dockflare.app/docs)
- Source docs in repository:
  - [Multi-Server Agent Guide](dockflare/app/templates/docs/Multi-Server-Agent.md)
  - [Using the Web UI](dockflare/app/templates/docs/Using-the-Web-UI.md)
  - [Managing DNS Zones](dockflare/app/templates/docs/Managing-DNS-Zones.md)
  - [Identity Providers](dockflare/app/templates/docs/Identity-Providers.md)

## Changelog

Release notes are maintained in [CHANGELOG.md](CHANGELOG.md).
