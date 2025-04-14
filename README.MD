# DockFlare: Cloudflare Tunnel Ingress Controller for Docker

[![Maintenance](https://img.shields.io/badge/Maintained%3F-yes-green.svg)](https://github.com/ChrispyBacon-dev/baconflip)
[![OS](https://img.shields.io/badge/os-linux%20%7C%20windows%20%7C%20macos-brightgreen)]()
[![CPU Architectures](https://img.shields.io/badge/CPU-x86%20%7C%20x64%20%7C%20ARM%20%7C%20ARM64-brightgreen)](https://en.wikipedia.org/wiki/Central_processing_unit)
[![Generic badge](https://img.shields.io/badge/Status-Alpha-yellow.svg)](https://shields.io/)
[![Docker Pulls](https://img.shields.io/docker/pulls/alplat/dockflare)](https://hub.docker.com/r/alplat/dockflare)
[![made-with-python](https://img.shields.io/badge/Made%20with-Python-1f425f.svg)](https://www.python.org/)
[![GitHub issues](https://img.shields.io/github/issues/alplat/dockflare)](https://github.com/alplat/dockflare/issues)
[![GitHub last commit](https://img.shields.io/github/last-commit/alplat/dockflare)](https://github.com/alplat/dockflare/commits/main)
[![GitHub commit activity](https://img.shields.io/github/commit-activity/m/alplat/dockflare)](https://github.com/alplat/dockflare/commits/main)


DockFlare automates Cloudflare Tunnel ingress rule management based on Docker container labels, simplifying public exposure of your Dockerized applications. It eliminates manual Cloudflare configuration, acting as a self-hosted ingress controller.

**Key Features:**

*   **Automated Cloudflare Tunnel Management:** Creates/uses a specified tunnel, retrieves Tunnel ID & Token.
*   **`cloudflared` Agent Lifecycle:** Deploys & manages the `cloudflared` container (using Tunnel Token).
*   **Dynamic Ingress via Docker Labels:**
    *   Monitors Docker events for containers with labels (prefix: `cloudflare.tunnel.`): `enable="true"`, `hostname="subdomain.example.com"`, `service="http://target:port"`.
    *   Automatically updates Cloudflare Tunnel configuration to match running, labeled containers.
*   **Graceful Deletion:** Configurable grace period before removing ingress rules when a container stops.
*   **State Persistence:** Saves `managed_rules` to `state.json` for restarts.
*   **Reconciliation:** On startup, ensures consistency between Docker containers, saved state, and Cloudflare configuration.
*   **Web UI:** Status dashboard with:
    *   Tunnel & agent status.
    *   Start/Stop agent controls.
    *   Managed ingress rule list with status, container ID, deletion time, and "Force Delete" option.

**Core Problem Solved:**

Simplifies exposing Docker services via Cloudflare Tunnel by automating configuration changes based on Docker container lifecycle events.
## Technical Implementation

*   **Language:** Python 3
*   **Core Libraries:**
    *   `requests`: Cloudflare API interaction.
    *   `docker`: Docker API interaction and event handling.
    *   `Flask`: Web UI.
    *   `python-dotenv`: Configuration management.
    *   `threading`: Background tasks.
*   **Deployment:** Runs as a Docker container, typically managed by `docker-compose.yml`. Requires mounting the Docker socket (`/var/run/docker.sock`) to interact with the Docker daemon.
*   **Configuration:**
    *   Primarily via an `.env` file (API Token, Account ID, Tunnel Name, optional grace period, labels, etc.).
    *   Docker labels on target application containers.
*   **Authentication:** Uses a Cloudflare API Token with Account:Cloudflare Tunnel:Edit permissions (and potentially Zone:DNS:Edit if explicit DNS management were added).

## Key Files

*   `app.py`: Main Python application code (Flask routes, API logic, Docker event handling, state management).
*   `Dockerfile`: Builds the application container, installing Python, dependencies, and `cloudflared`.
*   `docker-compose.yml`: Defines the service for running the application container and mounts the Docker socket.
*   `requirements.txt`: Lists Python dependencies.
*   `.env`: Stores sensitive configuration and parameters (API keys, IDs, tunnel name). **Do not commit this file!**
*   `state.json`: (Created at runtime) Persists the managed rules state.

## Getting Started

1.  **Clone the repository:**
    ```bash
    git clone <repository_url>
    cd <repository_directory>
    ```

2.  **Configure the .env file:**

    Copy the example configuration: cp .env.example .env, then edit .env to set the required variables.

    ```
    CF_API_TOKEN=<YOUR_CLOUDFLARE_API_TOKEN>
    CF_ACCOUNT_ID=<YOUR_CLOUDFLARE_ACCOUNT_ID>
    CF_ZONE_ID=<YOUR_CLOUDFLARE_ZONE_ID>
    TUNNEL_NAME=<DESIRED_TUNNEL_NAME>
    GRACE_PERIOD_SECONDS=28800  # Optional: Default 8 hours (8 * 60 * 60)
    ```

    *   `CF_API_TOKEN`:  Your Cloudflare API token with `Account:Cloudflare Tunnel:Edit` permissions.
    *   `CF_ACCOUNT_ID`: Your Cloudflare Account ID.
    *   `CF_ZONE_ID`: Your Cloudflare Zone ID (the domain where the DNS records will be created).
    *   `TUNNEL_NAME`: The name you want to give your Cloudflare Tunnel.
    *   `GRACE_PERIOD_SECONDS`: (Optional) The grace period in seconds before deleting an ingress rule after its associated container stops. Defaults to 8 hours.
    
3.  **Run with Docker Compose:**

    ```bash
    docker-compose up -d
    ```

4.  **Access the Web UI:**

    Open your web browser and navigate to the port you exposed in your `docker-compose.yml` (e.g., `http://localhost:5000`).

5.  **Label your Docker containers:**

    Add the necessary labels to your Docker containers:

    ```yaml
    labels:
      cloudflare.tunnel.enable: "true"
      cloudflare.tunnel.hostname: "my-service.example.com"
      cloudflare.tunnel.service: "http://my-service:8080"
      cloudflare.tunnel.zonename: "other-domain.com"
    ```

    *   Replace `"my-service.example.com"` with your desired public hostname.
    *   Replace `"http://my-service:8080"` with the internal URL of your service.
    *   Replace `"other-domain.com"`: (Optional) This label is only required when you want to expose the service on a domain different from the primary DNS zone configured via `CF_ZONE_ID` in the `.env` file.  It's used for multi-DNS domain support within the same Cloudflare account.

6. **Restart or redeploy the labeled docker containers**

    This will trigger the ingress controller to add rules as specified.

## Example `docker-compose.yml`

```yaml
version: "3.8"

services:
  cloudflare-tunnel-controller:
    image: alplat/dockflare:stable # Replace with your image or build from Dockerfile
    restart: unless-stopped
    ports:
      - "5000:5000"
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock
      - ./state.json:/app/state.json
    env_file:
      - .env
    environment:
      - FLASK_APP=app.py

networks:
  app-network:
    driver: bridge