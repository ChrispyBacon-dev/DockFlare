# Health Checks

DockFlare includes a dedicated health check endpoint that can be used with Docker's built-in health check mechanism. This allows Docker to monitor the health of the DockFlare application and automatically restart it if it becomes unresponsive.

## The `/ping` Endpoint

DockFlare exposes a simple HTTP endpoint at `/ping`.

*   **Purpose:** To provide a simple way for automated systems to check if the DockFlare web server is running and responsive.
*   **Authentication:** This endpoint is **exempt from authentication**. You do not need to be logged in to access it, which is what allows Docker's internal health check mechanism to use it.
*   **Healthy Response:** A healthy, running DockFlare application will respond to a request at `/ping` with an **HTTP 200 OK** status code.
*   **Version Information:** The body of the response from the `/ping` endpoint also contains the running version of the DockFlare application.

## How to Configure a Health Check in Docker Compose

You can add a `healthcheck` section to the `dockflare` service in your `docker-compose.yml` file to have Docker automatically monitor the application's health.

```yaml
services:
  dockflare:
    image: alplat/dockflare:stable
    container_name: dockflare
    restart: unless-stopped
    # ... other settings
    healthcheck:
      # The command to run to check health.
      # curl is used to make an HTTP request to the ping endpoint.
      test: ["CMD", "curl", "-f", "http://localhost:5000/ping"]
      # How often to run the check
      interval: 1m30s
      # How long to wait for a response
      timeout: 10s
      # How many consecutive failures before marking as unhealthy
      retries: 3
      # How long to wait after the container starts before running the first check
      start_period: 40s
```

### Breakdown of the `healthcheck` configuration:

*   `test`: This is the command that Docker runs inside the container. `curl -f` will make an HTTP request to the `/ping` endpoint and will exit with a non-zero status code if the response is not HTTP 200 OK.
*   `interval`: Docker will run this check every 90 seconds.
*   `timeout`: Docker will wait up to 10 seconds for the command to complete.
*   `retries`: If the check fails 3 times in a row, Docker will mark the container as `unhealthy`.
*   `start_period`: Docker will wait 40 seconds after the container has started before performing the first health check. This gives the application time to initialize properly.

With this configuration in place, you can check the health of your container by running `docker ps`. The status column will show `(healthy)` if the health check is passing. If the container becomes unhealthy, Docker will automatically restart it based on the `restart` policy (e.g., `unless-stopped`).
