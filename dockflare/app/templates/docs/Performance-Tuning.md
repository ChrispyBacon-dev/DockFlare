# Performance Tuning

For the vast majority of users, DockFlare's default settings provide a good balance of performance and resource utilization. However, in very large or highly dynamic environments, you may benefit from tuning some of the advanced performance-related parameters.

These settings are configured via environment variables in your `docker-compose.yml` file.

---

## `CLEANUP_INTERVAL_SECONDS`

This variable controls how often DockFlare's background task runs to clean up expired resources (i.e., rules from stopped containers whose grace period has elapsed).

*   **Default:** `60` seconds
*   **Description:** A shorter interval means that stale resources are removed more quickly from your Cloudflare configuration. A longer interval reduces the frequency of background checks, which can slightly lower resource usage.
*   **When to Tune:** If you have a very dynamic environment with many short-lived containers and want their resources cleaned up almost immediately, you could lower this value (e.g., to `30`). For most users, the default is fine.

**Example:**
```yaml
environment:
  - CLEANUP_INTERVAL_SECONDS=30
```

---

## `MAX_CONCURRENT_DNS_OPS`

This variable sets the maximum number of concurrent DNS operations (create, delete) that DockFlare will perform at one time.

*   **Default:** `3`
*   **Description:** This is a direct performance tuning knob for environments with a large number of services. When DockFlare starts up or when many containers are started at once, this setting limits how many parallel requests are made to the Cloudflare API for DNS changes.
*   **When to Tune:** If you are managing hundreds of services and notice that the initial startup or a mass deployment is slow to create all the DNS records, you can try increasing this value (e.g., to `5` or `10`). Be aware that setting this too high could lead to Cloudflare API rate limiting.

**Example:**
```yaml
environment:
  - MAX_CONCURRENT_DNS_OPS=5
```

---

## `RECONCILIATION_BATCH_SIZE`

This controls the batch size for various background reconciliation tasks.

*   **Default:** `3`
*   **Description:** Some background tasks in DockFlare process items in batches to avoid overwhelming the system or the Cloudflare API. This setting controls the size of those batches.
*   **When to Tune:** This is a very advanced setting. For most users, the default value should not be changed. If you have an extremely large number of rules (many hundreds or thousands), you might experiment with a slightly larger batch size, but it's generally not necessary.

**Example:**
```yaml
environment:
  - RECONCILIATION_BATCH_SIZE=5
```

---

## `SCAN_ALL_NETWORKS`

This variable changes how DockFlare discovers the IP address of containers.

*   **Default:** `false`
*   **Description:** By default, DockFlare expects that the target container is on the same Docker network as DockFlare itself. When `SCAN_ALL_NETWORKS` is set to `true`, DockFlare will inspect all the networks a container is attached to in order to find a shared network.
*   **When to Tune:** This should only be enabled if you have a complex Docker networking setup where your application containers are not on the same network as DockFlare. Be aware that enabling this can have a performance impact in environments with a very large number of Docker networks, as it requires more inspection work from DockFlare.

**Example:**
```yaml
environment:
  - SCAN_ALL_NETWORKS=true
```
