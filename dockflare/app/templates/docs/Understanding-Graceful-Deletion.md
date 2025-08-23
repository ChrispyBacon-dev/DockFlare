# Understanding Graceful Deletion

When you stop a container managed by DockFlare, you might notice that its corresponding public hostname doesn't immediately go offline. This is due to a feature called **Graceful Deletion**.

## What is Graceful Deletion?

Instead of instantly deleting the Cloudflare ingress rule and DNS record the moment a container stops, DockFlare marks the rule as **"pending deletion"** and starts a timer.

The associated Cloudflare resources (the ingress rule and DNS record) will only be permanently deleted after this timer, known as the **grace period**, expires.

## Why is This Useful?

This feature is designed to prevent service interruptions in common operational scenarios:

*   **Container Updates:** When you update a container image (`docker compose up -d`), Docker typically stops the old container and starts a new one. Without a grace period, your service would be inaccessible for a short time. With graceful deletion, the DNS record and ingress rule remain active, and DockFlare simply re-associates them with the new container, resulting in zero downtime.
*   **Temporary Restarts:** If you need to stop a container for a moment to change a setting and then restart it, the grace period ensures that your public-facing configuration remains intact.

## The `GRACE_PERIOD_SECONDS` Variable

The duration of this grace period is controlled by the `GRACE_PERIOD_SECONDS` environment variable, which you can set in your `docker-compose.yml` file.

*   The default value is `600` seconds (10 minutes).
*   You can adjust this value to suit your needs. A shorter period makes cleanup faster, while a longer period provides a larger window for container restarts.

**Example:**
```yaml
services:
  dockflare:
    image: alplat/dockflare:stable
    # ... other settings
    environment:
      - GRACE_PERIOD_SECONDS=3600 # Set a 1-hour grace period
```

## How it Works in Practice

1.  **Container Stopped:** You run `docker stop my-app`.
2.  **Pending Deletion:** DockFlare detects the stop event. In the Web UI, the rule for `my-app.example.com` will now show its status as **"pending_deletion"** and display the time at which it is scheduled to be deleted.
3.  **The Two Scenarios:**
    *   **Scenario A: Grace Period Expires:** If the container remains stopped and the grace period (e.g., 10 minutes) expires, DockFlare's background cleanup task will run. It will delete the ingress rule from your Cloudflare Tunnel and remove the CNAME DNS record.
    *   **Scenario B: Container Restarts:** If you start the container again (`docker start my-app`) **before** the grace period expires, DockFlare will detect the start event. It will see that the rule is pending deletion, cancel the deletion, and change its status back to **"active"**. Your service continues to operate seamlessly.
