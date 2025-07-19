If you don't already have a monitoring stack, here is a minimal `docker-compose` setup to get you started quickly.

#### 1. Directory Structure
Create the following folders and files alongside your main `docker-compose.yml`:

```
.
├── docker-compose.yml   # Your main compose file
├── prometheus.yml         # New file for Prometheus configuration
└── grafana-provisioning/  # New folder
    └── datasources/       # New sub-folder
        └── datasource.yml # New file for Grafana configuration
```

#### 2. File Contents

**A) `docker-compose.yml`**

Add the following services to your existing `docker-compose.yml` file:

```yaml
services:
  # ... your existing dockflare service ...

  prometheus:
    image: prom/prometheus:latest
    container_name: prometheus
    restart: unless-stopped
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml
      - ./prometheus_data:/prometheus # Persistent data for Prometheus
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
    networks:
      - your-dockflare-network # <-- IMPORTANT: Use the same network as DockFlare
    labels:
      - "dockflare.enable=true"
      - "dockflare.hostname=prometheus.your-domain.com"
      - "dockflare.service=http://prometheus:9090"

  grafana:
    image: grafana/grafana-oss:latest
    container_name: grafana
    restart: unless-stopped
    volumes:
      - ./grafana_data:/var/lib/grafana # Persistent data for Grafana
      - ./grafana-provisioning:/etc/grafana/provisioning
    networks:
      - your-dockflare-network # <-- IMPORTANT: Use the same network as DockFlare
    labels:
      - "dockflare.enable=true"
      - "dockflare.hostname=metrics.your-domain.com" # Exposes Grafana
      - "dockflare.service=http://grafana:3000"
```
> **Permissions Tip:** If Grafana or Prometheus fail to start with a "Permission denied" error, you may need to set the ownership of the host directories. Run `sudo chown -R 472:472 ./grafana_data` for Grafana and `sudo chown -R 65534:65534 ./prometheus_data` for Prometheus.

**B) `prometheus.yml`**

This file tells Prometheus where to find your `cloudflared` agent.

```yaml
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: 'cloudflared'
    static_configs:
      - targets: ['your-cloudflared-agent-name:2000']
        # --- IMPORTANT ---
        # 1. Replace 'your-cloudflared-agent-name' with the actual name of your agent container (e.g., 'cloudflared-agent-green-bern').
        # 2. Replace '2000' with the port you set for CLOUDFLARED_METRICS_PORT.
```

**C) `grafana-provisioning/datasources/datasource.yml`**

This automatically adds Prometheus as a data source in Grafana.

```yaml
apiVersion: 1

datasources:
  - name: Prometheus
    type: prometheus
    access: proxy
    url: http://prometheus:9090
    isDefault: true
```

#### 3. How to Use

1.  **Start the Stack:** Run `docker-compose up -d`.
2.  **Check Prometheus:** Navigate to your Prometheus URL (e.g., `http://prometheus.your-domain.com`). Go to **Status -> Targets**. The `cloudflared` endpoint should be **UP**.
3.  **Import Dashboard:** Navigate to your Grafana URL (e.g., `http://metrics.your-domain.com`), log in (default: `admin`/`admin`), and import the `dashboard.json` file provided in the `examples/` directory of the DockFlare repository.
4.  **View Your Metrics!**