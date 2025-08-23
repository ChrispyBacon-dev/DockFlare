# Internal vs. External `cloudflared`

DockFlare can operate in two modes for managing the `cloudflared` agent, which is the piece of software that actually creates the persistent connection between your server and the Cloudflare network. Understanding these two modes is key to choosing the right setup for your environment.

## Internal Mode (Default)

In Internal Mode, DockFlare takes full responsibility for managing the `cloudflared` agent.

### How it Works
When DockFlare starts, it will automatically:
1.  Create a dedicated Docker container running the `cloudflare/cloudflared` image.
2.  Configure this agent container to connect to your Cloudflare account and use the tunnel specified in your DockFlare settings.
3.  Ensure the agent is running and restart it if it fails.
4.  Automatically apply any relevant settings, such as enabling the Prometheus metrics endpoint.

This is the **default and recommended** mode for most users.

### Pros
*   **Simplicity:** It's a "zero-configuration" setup. DockFlare handles everything for you.
*   **Guaranteed Compatibility:** DockFlare ensures that the agent is configured in a way it can work with.
*   **Centralized Management:** Everything related to your tunnels is managed by DockFlare.

### Cons
*   **Less Control:** You have limited control over the `cloudflared` agent's configuration beyond what DockFlare exposes.

---

## External `cloudflared` Mode

In External Mode, you are responsible for running and managing the `cloudflared` agent yourself. DockFlare will connect to this existing agent instead of creating its own.

### How it Works
DockFlare will **not** create a `cloudflared` container. Instead, it will assume that you have a `cloudflared` agent running somewhere that it can use. This could be:
*   A `cloudflared` process running directly on the host OS (e.g., as a `systemd` service).
*   A `cloudflared` container that you manage yourself with a separate `docker-compose.yml` file or Docker run command.
*   A `cloudflared` agent running on a different machine entirely.

This is an **advanced mode** intended for users with specific needs or complex existing setups.

### Pros
*   **Maximum Control:** You have full control over the `cloudflared` agent, including its version, command-line arguments, and lifecycle.
*   **Integration with Existing Setups:** Perfect if you already have a `cloudflared` agent running for other purposes.
*   **Decoupling:** Decouples the lifecycle of DockFlare from the lifecycle of the `cloudflared` agent.

### Cons
*   **Complexity:** You are responsible for ensuring the `cloudflared` agent is running, configured correctly, and connected to the correct tunnel.
*   **Configuration Overhead:** You need to configure DockFlare to use this external agent.

### How to Enable External Mode
To enable External Mode, you must set the following environment variables for the DockFlare container:

*   `USE_EXTERNAL_CLOUDFLARED=true`: This enables the external mode.
*   `EXTERNAL_TUNNEL_ID`: This must be set to the UUID of the tunnel that your external `cloudflared` agent is configured to use.

When these variables are set, DockFlare will skip its internal agent management and will instead send all ingress rule configurations to the tunnel specified by `EXTERNAL_TUNNEL_ID`.
