# DockFlare: Cloudflare Tunnel Ingress Controller

[![Maintenance](https://img.shields.io/badge/Maintained%3F-yes-green.svg)](https://github.com/ChrispyBacon-dev/baconflip)
[![OS](https://img.shields.io/badge/os-linux%20%7C%20windows%20%7C%20macos-brightgreen)]()
[![CPU Architectures](https://img.shields.io/badge/CPU-x86_64%20%7C%20arm64-brightgreen)](https://en.wikipedia.org/wiki/Central_processing_unit)
[![Generic badge](https://img.shields.io/badge/Status-Alpha-yellow.svg)](https://shields.io/)
[![Docker Pulls](https://img.shields.io/docker/pulls/alplat/dockflare)](https://hub.docker.com/r/alplat/dockflare)
[![made-with-python](https://img.shields.io/badge/Made%20with-Python-1f425f.svg)](https://www.python.org/)
[![GitHub issues](https://img.shields.io/github/issues/ChrispyBacon-dev/dockflare)](https://github.com/ChrispyBacon-dev/dockflare/issues)
[![GitHub last commit](https://img.shields.io/github/last-commit/ChrispyBacon-dev/dockflare)](https://github.com/ChrispyBacon-dev/dockflare/commits/stable)
[![GitHub commit activity](https://img.shields.io/github/commit-activity/m/ChrispyBacon-dev/dockflare)](https://github.com/ChrispyBacon-dev/dockflare/commits/stable)


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

**Modern Web UI showing the status of Ingress Rules and Real Time Monitoring**

![Web ui example](images/status_web.png)

## Getting Started

There are two main ways to get DockFlare running:

1.  **Quick Start:** Directly use Docker Compose with the provided configuration.
2.  **From Repository:** Clone the repository first, then configure and run.

Choose the method that best suits your needs.

---

### Prerequisites

*   Docker: [Install Docker](https://docs.docker.com/engine/install/)
*   Docker Compose: [Install Docker Compose](https://docs.docker.com/compose/install/)

---

### Option 1: Quick Start (Using Docker Compose)

This method allows you to run DockFlare quickly without cloning the entire repository.

1.  **Create `docker-compose.yml`:**
    Create a file named `docker-compose.yml` in a directory of your choice and paste the following content:

    ```yaml
    version: '3.8'
    services:
      cloudflare-tunnel-manager:
        image: alplat/dockflare:stable # Pre-built image (currently x86_64/amd64 only)
        container_name: dockflare
        restart: unless-stopped
        ports:
          - "5000:5000" # Exposes the Web UI on port 5000
        env_file:
          - .env
        volumes:
          - /var/run/docker.sock:/var/run/docker.sock:ro # Required to monitor Docker events
          - dockflare_data:/app/data # Persistent storage for state
        networks:
          - cloudflare-net
        environment:
          - STATE_FILE_PATH=/app/data/state.json # Path to state file inside the container
          - TZ=Europe/Zurich # Optional: Set your timezone, e.g., America/New_York
    volumes:
      dockflare_data:
    networks:
      cloudflare-net:
      name: cloudflare-net # Creates/uses a dedicated network for the tunnel
    ```

2.  **Create and Configure `.env`:**
    Create a file named `.env` in the *same directory* as your `docker-compose.yml`. Add your Cloudflare details:

    ```dotenv
    # --- Required Cloudflare Configuration ---
    CF_API_TOKEN=<YOUR_CLOUDFLARE_API_TOKEN>
    CF_ACCOUNT_ID=<YOUR_CLOUDFLARE_ACCOUNT_ID>
    CF_ZONE_ID=<YOUR_CLOUDFLARE_ZONE_ID> # Primary domain for DNS records
    TUNNEL_NAME=<DESIRED_TUNNEL_NAME>    # e.g., my-dockflare-tunnel

    # --- Optional Configuration ---
    GRACE_PERIOD_SECONDS=28800 # Default: 8 hours (8 * 60 * 60). Time before deleting rules for stopped containers.
    # LOG_LEVEL=INFO           # Optional: Set log level (DEBUG, INFO, WARNING, ERROR). Default: INFO
    ```

    *   `CF_API_TOKEN`: Your Cloudflare API token. Requires `Account:Cloudflare Tunnel:Edit` permission. [How to create](https://developers.cloudflare.com/api/tokens/create/).
    *   `CF_ACCOUNT_ID`: Your Cloudflare Account ID. [Find your Account ID](https://developers.cloudflare.com/fundamentals/get-started/basic-tasks/find-account-and-zone-ids/).
    *   `CF_ZONE_ID`: Your Cloudflare Zone ID for the primary domain where DNS records will be created. [Find your Zone ID](https://developers.cloudflare.com/fundamentals/get-started/basic-tasks/find-account-and-zone-ids/).
    *   `TUNNEL_NAME`: A unique name for your Cloudflare Tunnel (e.g., `my-app-tunnel`).
    *   `GRACE_PERIOD_SECONDS`: (Optional) Grace period in seconds before deleting ingress rules after a container stops. Defaults to `28800` (8 hours).
    *   `LOG_LEVEL`: (Optional) Set the application's logging verbosity. Defaults to `INFO`.

3.  **Run with Docker Compose:**
    Open your terminal in the directory containing the `docker-compose.yml` and `.env` files, then run:

    ```bash
    docker compose up -d
    ```

---

### Option 2: From Cloned Repository

This method involves cloning the repository, which gives you access to the example files directly.

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/ChrispyBacon-dev/DockFlare.git
    cd DockFlare
    ```

2.  **Configure the `.env` file:**
    Copy the example configuration file and then edit it with your details:

    ```bash
    cp .env.example .env
    nano .env # or use your preferred text editor
    ```

    Fill in the following variables in the `.env` file:
    ```dotenv
    # --- Required Cloudflare Configuration ---
    CF_API_TOKEN=<YOUR_CLOUDFLARE_API_TOKEN>
    CF_ACCOUNT_ID=<YOUR_CLOUDFLARE_ACCOUNT_ID>
    CF_ZONE_ID=<YOUR_CLOUDFLARE_ZONE_ID> # Primary domain for DNS records
    TUNNEL_NAME=<DESIRED_TUNNEL_NAME>    # e.g., my-dockflare-tunnel

    # --- Optional Configuration ---
    GRACE_PERIOD_SECONDS=28800 # Default: 8 hours (8 * 60 * 60). Time before deleting rules for stopped containers.
    # LOG_LEVEL=INFO           # Optional: Set log level (DEBUG, INFO, WARNING, ERROR). Default: INFO
    ```
    *   Refer to the variable descriptions in **Option 1, Step 2** for details on each setting.

3.  **Run with Docker Compose:**
    Ensure you are in the `DockFlare` directory (where the `docker-compose.yml` file is located) and run:

    ```bash
    docker compose up -d
    ```

---

### Architecture Support

*   **Currently Supported:** The pre-built Docker image (`alplat/dockflare:stable`) now supports both `x86_64` / `amd64` and `arm64` architectures.
*   **Automatic Architecture Detection:** The `Dockerfile` dynamically detects the system architecture and downloads the appropriate `cloudflared` binary during the build process.

---

### Next Steps

1.  **Access the Web UI:**
    Once the container is running, open your web browser and navigate to the port exposed in your `docker-compose.yml` (e.g., `http://localhost:5000` or `http://<your-server-ip>:5000`).

2.  **Label your Docker containers:**
    To expose services through the Cloudflare Tunnel managed by DockFlare, add labels to your *other* service containers (e.g., in their `docker-compose.yml`):

    ```yaml
    services:
      my-web-app:
        image: nginx:latest # Example service
        labels:
          # --- DockFlare Labels ---
          cloudflare.tunnel.enable: "true" # Required: Tells DockFlare to manage this service
          cloudflare.tunnel.hostname: "my-service.example.com" # Required: Your public hostname
          cloudflare.tunnel.service: "http://my-web-app:80" # Required: Internal service URL (use container name/alias and port)
          cloudflare.tunnel.no_tls_verify: "true" # Optional: Disables TLS verification for this service
          # cloudflare.tunnel.zonename: "other-domain.com" # Optional: Use if hostname is on a different zone than CF_ZONE_ID
    ```
    *   Replace `"my-service.example.com"` with the desired public hostname (must be within a zone managed by your Cloudflare account).
    *   Replace `"http://my-web-app:80"` with the internal URL of your service (use the service/container name and the port it listens on *within the Docker network*).
    *   `cloudflare.tunnel.zonename`: (Optional) Only needed if the `hostname` belongs to a *different* Cloudflare Zone than the one specified by `CF_ZONE_ID` in your `.env` file. Both zones must be under the same Cloudflare Account (`CF_ACCOUNT_ID`).
    *   `cloudflare.tunnel.no_tls_verify`: (Optional) Disables TLS verification for this service.

3.  **Restart or Deploy Labeled Containers:**
    After adding the labels, (re)start the labeled containers (e.g., `docker-compose up -d my-web-app`). DockFlare will detect the labels and automatically configure the Cloudflare Tunnel ingress rules.

## Configuring Cloudflare Credentials (`.env` file)

DockFlare needs credentials to interact with your Cloudflare account to manage tunnels and DNS records. You'll need to provide these in the `.env` file.

**1. Finding Your Account ID (`CF_ACCOUNT_ID`)**

Your Account ID identifies your entire Cloudflare account.

*   Log in to the [Cloudflare Dashboard](https://dash.cloudflare.com/).
*   Select any of your domain names (zones).
*   On the domain's **Overview** page, scroll down the right-hand sidebar.
*   You'll find your **Account ID** listed there. Copy this value.
    *   *Direct Link (after login):* You can often find it quickly here: `https://dash.cloudflare.com/?to=/:account/support` (Look under "Account Details").

**2. Finding Your Zone ID (`CF_ZONE_ID`)**

Your Zone ID identifies a specific domain (zone) managed within your Cloudflare account.

*   **Primary Zone:** You must specify *one* Zone ID here. This acts as the **primary** or **default** zone where DockFlare will create DNS CNAME records for your services *unless* you explicitly specify a different zone using labels on a container.
*   **Multi-Zone Support:** DockFlare *can* manage DNS records across multiple zones within the same Cloudflare account (identified by `CF_ACCOUNT_ID`). To use a zone *other* than this primary one for a specific service, you will use the `cloudflare.tunnel.zonename` label on that service's container (see "Label your Docker containers" section below).
*   **API Token Requirement:** Ensure the API Token you create (see step 3) has `Zone:DNS:Edit` permissions covering *all* the zones you intend to use, including this primary zone and any others you might specify with labels. Granting access to "All zones from an account" during token creation is the simplest way to enable this flexibility.

*   **How to Find the Primary Zone ID:**
    1.  Log in to the [Cloudflare Dashboard](https://dash.cloudflare.com/).
    2.  Click on the **specific domain name** (e.g., `example.com`) that you want to designate as your **primary** zone for DockFlare.
    3.  On that domain's **Overview** page, scroll down the right-hand sidebar.
    4.  You'll find the **Zone ID** listed just below the Account ID. Copy this value to use for `CF_ZONE_ID` in your `.env` file.

**3. Creating the API Token (`CF_API_TOKEN`)**

For security, DockFlare requires an API **Token** with specific, limited permissions, rather than your Global API Key.

*   **Permissions Needed:**
    *   `Account` > `Cloudflare Tunnel` > `Edit`: Allows DockFlare to create, list, and delete Cloudflare Tunnels within your account.
    *   `Zone` > `DNS` > `Edit`: Allows DockFlare to create and delete DNS records (specifically CNAME records pointing to your tunnel) within your zones.

*   **Steps to Create the Token:**
    1.  Log in to the [Cloudflare Dashboard](https://dash.cloudflare.com/).
    2.  Click your **profile icon** in the top right corner and select "**My Profile**".
    3.  Navigate to the "**API Tokens**" tab on the left sidebar.
    4.  Click the "**Create Token**" button.
    5.  Scroll down to the "**Custom token**" section and click "**Get started**".
    6.  **Token Name:** Give your token a descriptive name, e.g., `DockFlare-Manager`.
    7.  **Permissions:** Configure the following permissions:
        *   **Permission 1 (Tunnel Management):**
            *   Select: `Account`
            *   Select: `Cloudflare Tunnel`
            *   Select: `Edit`
        *   **Permission 2 (DNS Management):**
            *   Click "**+ Add more**"
            *   Select: `Zone`
            *   Select: `DNS`
            *   Select: `Edit`
    8.  **Account Resources:**
        *   For the `Account - Cloudflare Tunnel - Edit` permission row, ensure it's set to:
            *   `Include` > `Specific account` > `[Your Account Name]` (Select your main account).
    9.  **Zone Resources:**
        *   For the `Zone - DNS - Edit` permission row, configure it to grant access to the zones DockFlare might need:
            *   `Include` > `All zones from an account` > `[Your Account Name]`
            *   *(This is the most flexible option, allowing DockFlare to manage DNS for the primary `CF_ZONE_ID` and any other zones you might specify using the `cloudflare.tunnel.zonename` label later.)*
            *   *(Alternatively, if you *only* ever plan to use the single zone defined by `CF_ZONE_ID`, you could select `Include` > `Specific zone` > `[Your Primary Domain Zone]`. However, using "All zones from an account" is generally recommended for flexibility.)*
    10. **Client IP Address Filtering (Optional but Recommended):** If you know the static IP address(es) from which DockFlare will be running, you can restrict the token to only work from those IPs for added security.
    11. **TTL (Optional):** Set an expiration date for the token if desired.
    12. Click "**Continue to summary**".
    13. Review the permissions and resource scopes carefully. Ensure they match the requirements (`Account:Cloudflare Tunnel:Edit`, `Zone:DNS:Edit`).
    14. Click "**Create Token**".
    15. **Important:** Cloudflare will now display your API Token. **Copy this token immediately** and store it securely. You will **not** be able to see it again after leaving this page.

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