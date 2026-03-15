# DockFlare Agent & Multi-Server Architecture

DockFlare 3.0 introduces a distributed execution model that lets you manage Cloudflare tunnels across multiple Docker hosts. The DockFlare **Master** coordinates configuration, while lightweight **Agents** run alongside your workloads and keep their local `cloudflared` instance in sync with the master.

This guide explains the architecture, security model, and step-by-step workflow for deploying agents.

---

## Why Agents?

* **Decouple compute from ingress** – keep workloads close to users while maintaining a single control plane.
* **Per-host visibility** – monitor heartbeat, tunnel status, and command history for each agent.
* **Least-privilege tokens** – revoke compromised agents without touching the master or other hosts.
* **Resilient updates** – agents continue serving traffic with their last-known configuration if the master is temporarily unavailable.

---

## Components at a Glance

| Component | Responsibility |
|-----------|----------------|
| **Master (DockFlare)** | Hosts the web UI, stores state, reconciles desired ingress rules, issues commands. |
| **Redis** | Backplane for caching, agent heartbeats, and queued commands. |
| **DockFlare Agent** | Headless container that watches local Docker events, executes commands, and runs `cloudflared`. |
| **cloudflared** | Handles the actual tunnel connection to Cloudflare per agent. |

The master and Redis typically run together, while agents run next to workloads (potentially on remote networks).

---

## Prerequisites

* DockFlare Master ≥ v3.0 with Redis configured (`REDIS_URL` set). Optionally specify `REDIS_DB_INDEX` to isolate data from other containers using the same Redis instance.
* Cloudflare API token with Tunnel + Access permissions (same as previous versions).
* Docker runtime on every host you plan to manage.
* (Optional) Dedicated network segment or VPN between master and agents if you do not expose the master publicly.

---

## Workflow Overview

1. **Generate an agent API key** in the DockFlare UI (`Agents → Generate Key`).
2. **Deploy the DockFlare Agent** container on the remote host, passing the master URL and key.
3. The agent **registers** with the master and appears with status *Pending*.
4. From the master UI, **enrol** the agent – assign or create a Cloudflare tunnel for that host.
5. The master queues commands; the agent **polls**, applies config, and reports status/heartbeat. DockFlare auto-detects the target zone for each hostname (falling back to the default zone only when detection fails).
6. As containers start/stop on the agent host, the agent streams events back to the master which updates DNS, Access policies, and tunnel ingress rules.

---

## Deploying the DockFlare Agent

> ℹ️ The agent will be published as `alplat/dockflare-agent`. Until the public repository is live, you can build from the `DockFlare-agent` source tree included with DockFlare 3.0.

```bash
# Example environment file used by the agent container
DOCKFLARE_MASTER_URL=https://dockflare.example.com
DOCKFLARE_API_KEY=agent_api_key_goes_here
DOCKER_HOST=tcp://docker-socket-proxy:2375
# control the docker image used for the managed cloudflared tunnel (accepts repo:tag or repo@sha256:<digest>)
CLOUDFLARED_IMAGE=cloudflare/cloudflared:2025.9.0
LOG_LEVEL=info
TZ=Europe/Zurich
```

Minimal `docker-compose.yml` on the agent host:

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
      - EXEC=1
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock
    networks:
      - dockflare-internal
      
  dockflare-agent:
    image: alplat/dockflare-agent:latest
    container_name: dockflare-agent
    restart: unless-stopped
    env_file:
      - .env
    environment:
      - DOCKER_HOST=${DOCKER_HOST:-tcp://docker-socket-proxy:2375}
      - TZ=${TZ:-UTC}
      - LOG_LEVEL=${LOG_LEVEL:-info}
    volumes:
      - agent_data:/app/data
    depends_on:
      - docker-socket-proxy
    networks:
      - cloudflare-net
      - dockflare-internal

volumes:
  agent_data:

networks:
  cloudflare-net:
    name: cloudflare-net
    external: true
  dockflare-internal:
    name: dockflare-internal
```

- Run `docker network create cloudflare-net` once to provision the shared network used by the master and agents.
- The socket proxy limits the Docker API surface area the agent can reach; only the capabilities set to `1` are exposed.
- The agent image runs as the unprivileged `dockflare` user (UID/GID 65532). Ensure mounted directories like `/app/data` are writable by that account or rebuild with `DOCKFLARE_UID/DOCKFLARE_GID` to match your host.
- Populate a `.env` file with `DOCKFLARE_MASTER_URL` and `DOCKFLARE_API_KEY`; optional overrides (for example `LOG_LEVEL` or `DOCKER_HOST`) can be provided the same way.

---

## Security Model

* **Master API key** – protects the administrative API. The UI only exposes it after you click *Show master API key*.
* **Agent API keys** – unique per agent. Revoking a key immediately blocks further registration/commands from that host.
* **Redis** – used for queues and caches; secure it (password + network ACLs) if running outside a trusted LAN.
* **Transport** – run the master behind HTTPS (e.g., via Cloudflare Access) so agent traffic is encrypted.
* **Least-privilege runtime** – the agent container runs as the `dockflare` user (UID/GID 65532) and relies on the socket proxy to keep Docker access scoped to container inspection and lifecycle control.

### Recommended Hardening

1. Store agent keys in a vault/password manager; rotate regularly.
2. **Do not disable password login** - use OAuth/OIDC providers instead for single sign-on convenience without security risks. If you must disable password login, understand that this creates a Docker network security vulnerability where any container on the same network can bypass external authentication. See [Accessing the Web UI - Disabling Password Login](Accessing-the-Web-UI.md#disabling-password-login) for full security implications.
3. Use separate tunnels per agent for least-privilege isolation.
4. Monitor `Agents` page for heartbeat gaps – offline nodes can be removed directly from the UI.

---

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| Agent stuck in `pending` | Ensure it has registered with the correct API key and enrol it from the UI. |
| Commands never clear | Confirm Redis connectivity and that the agent container clocks are in sync. |
| DNS not updating | The master must reach Cloudflare and the agent must send container events; verify `docker logs dockflare-agent`. |
| Heartbeat offline | Check network path between agent and master; firewall or TLS issues are common causes. |

---

## Next Steps

* Review the updated Quick Start in the repository README to ensure Redis is configured.
* Check the changelog for breaking changes and migration notes.
* Subscribe to the public DockFlare Agent repository once it is published to stay up-to-date with releases.

Happy tunnelling! 🚇
