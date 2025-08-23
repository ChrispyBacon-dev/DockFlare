# Switching Between Modes

You can switch DockFlare between **Internal** (default) and **External** `cloudflared` modes at any time. This guide explains the process for a smooth transition.

For a detailed comparison of the two modes, please see the [Internal vs. External `cloudflared`](Internal-vs-External-cloudflared.md) page.

---

## Switching from Internal to External Mode

This process involves setting up your own `cloudflared` agent and then telling DockFlare to use it.

**Step 1: Set Up Your External `cloudflared` Agent**

First, you need to set up and run your own `cloudflared` agent. This could be a process on the host OS or another Docker container.

*   Ensure it is configured to use a specific Cloudflare Tunnel.
*   Make a note of the **Tunnel ID** (UUID).
*   Start the agent and confirm it is running correctly and shows as "connected" in your Cloudflare dashboard.

**Step 2: Reconfigure and Restart DockFlare**

Next, you need to update the environment variables for your DockFlare container to tell it to switch to external mode.

In your `docker-compose.yml`:
```yaml
services:
  dockflare:
    image: alplat/dockflare:stable
    # ... other settings
    environment:
      # Enable external mode
      - USE_EXTERNAL_CLOUDFLARED=true
      # Provide the ID of your running tunnel
      - EXTERNAL_TUNNEL_ID=your-tunnel-uuid-goes-here
```

**Step 3: Deploy the Change**

Run `docker compose up -d` to recreate the DockFlare container with the new environment variables.

When the updated DockFlare container starts:
1.  It will detect that `USE_EXTERNAL_CLOUDFLARED` is `true`.
2.  It will **stop and remove** its own managed `cloudflared-agent` container.
3.  It will begin sending all its ingress rule configurations to the tunnel specified by `EXTERNAL_TUNNEL_ID`.

Your services will now be served by your externally managed `cloudflared` agent.

---

## Switching from External to Internal Mode

This process is simpler as it involves letting DockFlare take back control.

**Step 1: Reconfigure DockFlare**

Remove the external mode environment variables from your DockFlare `docker-compose.yml` file.

```yaml
services:
  dockflare:
    image: alplat/dockflare:stable
    # ... other settings
    environment:
      # Remove the following two lines
      # - USE_EXTERNAL_CLOUDFLARED=true
      # - EXTERNAL_TUNNEL_ID=your-tunnel-uuid-goes-here
```

**Step 2: Deploy the Change**

Run `docker compose up -d` to recreate the DockFlare container.

When the updated DockFlare container starts:
1.  It will detect that `USE_EXTERNAL_CLOUDFLARED` is `false`.
2.  It will automatically **create, configure, and start** its own internal `cloudflared-agent` container.
3.  It will configure this new agent to use the tunnel name defined in your DockFlare settings.

**Step 3: Decommission Your External Agent**

Once you have confirmed that the new internal agent is running correctly and serving traffic, you can safely stop and remove your own `cloudflared` agent.
