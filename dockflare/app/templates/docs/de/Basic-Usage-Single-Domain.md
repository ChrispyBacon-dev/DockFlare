# Grundlegende Nutzung (Einzelne Domain)

Dieser Leitfaden veranschaulicht den häufigsten Anwendungsfall für DockFlare: Die Freigabe eines einzelnen Docker-Containers für das Internet unter einem öffentlichen Hostnamen.

## Voraussetzungen

Bevor Sie beginnen, stellen Sie Folgendes sicher:
1.  Sie haben den [Quick Start](Quick-Start-Docker-Compose.md) Guide (Schnellstart) abgeschlossen.
2.  DockFlare läuft und ist mit Ihrem Cloudflare-Konto verbunden.
3.  Sie haben einen Dienst, den Sie exponieren möchten (wir werden in diesem Beispiel `nginx` verwenden).

## Beispiel: Freigabe eines NGINX-Containers

Nehmen wir an, Sie möchten einen Standard-NGINX-Webserver unter dem Hostnamen `nginx.example.com` bereitstellen.

### 1. Fügen Sie den Service zu Ihrer `docker-compose.yml` hinzu

Bearbeiten Sie Ihre `docker-compose.yml`-Datei, um den Dienst `nginx` aufzunehmen. Der entscheidende Punkt ist, die `dockflare.*` Labels zu seiner Konfiguration hinzuzufügen.

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
      - INFO=1
      - EXEC=1
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock
    networks:
      - dockflare-internal

  dockflare-init:
    image: alpine:3.20
    command: ["sh", "-c", "chown -R 65532:65532 /app/data"]
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
      - "5000:5000"
    volumes:
      - dockflare_data:/app/data
    environment:
      - REDIS_URL=redis://redis:6379/0
      - REDIS_DB_INDEX=0  # Optional: specify Redis database index (0-15) for isolation from other containers
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

  # Add your new service here
  nginx-webserver:
    image: nginx:latest
    container_name: my-nginx
    restart: unless-stopped
    networks:
      - cloudflare-net
    labels:
      - "dockflare.enable=true"
      - "dockflare.hostname=nginx.example.com"
      - "dockflare.service=http://nginx-webserver:80"
      # Optional: Apply public access with zone protection bypass
      - "dockflare.access.group=public-default-bypass"

  redis:
    image: redis:7-alpine
    container_name: dockflare-redis
    restart: unless-stopped
    command: ["redis-server", "--save", "", "--appendonly", "no"]
    volumes:
      - dockflare_redis:/data
    networks:
      - dockflare-internal

volumes:
  dockflare_data:
  dockflare_redis:

networks:
  cloudflare-net:
    name: cloudflare-net
    external: true
  dockflare-internal:
    name: dockflare-internal
```
> **Warum Redis?** DockFlare nutzt Redis für Caching, Log-Streaming und agentenübergreifende Kommunikation. Wenn Sie Redis im privaten Netzwerk `dockflare-internal` betreiben, bleibt er nur für DockFlare erreichbar, während Workloads weiterhin sicher in `cloudflare-net` isoliert sind.

### 2. Labels verstehen

*   `dockflare.enable=true`: Dies teilt DockFlare mit, diesen Container zu verwalten.
*   `dockflare.hostname=nginx.example.com`: Dies ist die öffentliche URL, unter der Ihr Dienst erreichbar sein wird. DockFlare erstellt einen DNS-Eintrag für diesen Hostnamen in Ihrem Cloudflare-Konto.
*   `dockflare.service=http://nginx-webserver:80`: Bestimmt intern das Ziel des Cloudflare Tunnels (hier der NGINX-Container).
*   `dockflare.access.group=public-default-bypass`: (Optional) Nutzt die Systemrichtlinie zum Bypass, um direkten Zugriff zu gewähren, und übergeht alle `*.example.com`-Zonen-Sperren, die auf Access gesetzt sind.

### 3. Den Dienst bereitstellen

Speichern Sie Ihre `docker-compose.yml` Datei und führen Sie den folgenden Befehl aus, um den neuen Dienst zu starten:

```bash
docker compose up -d
```

### 4. Überprüfung

DockFlare wird den neuen Container erkennen und automatisiert folgende Aktionen durchführen:
1.  Hinzufügen einer Ingress-Regel zu Ihrem Tunnel für `nginx.example.com`.
2.  Erstellen eines CNAME-Eintrages auf Cloudflare.

Sie können dies auf verschiedene Arten überprüfen:
*   **DockFlare Web UI**: Der Dienst `nginx.example.com` erscheint auf dem Dashboard.
*   **Cloudflare Dashboard**: Der neue CNAME Eintrag wird in der DNS Konfiguration angezeigt und die neue Route existiert im Zero Trust Tunnel.

Nach kurzer Zeit für die DNS-Propagation sollten Sie `https://nginx.example.com` im Browser aufrufen und die standardmäßige NGINX-Begrüßungsseite sehen können.


## Backup & Wiederherstellung im Detail

DockFlare bietet einen integrierten Backup-Flow, mit dem Sie eine Instanz in wenigen Minuten migrieren oder wiederherstellen können.

### Was das Backup-Archiv enthält

Wenn Sie ein Backup unter **Settings → Backup & Restore** (oder im Onboarding-Assistenten) herunterladen, erzeugt DockFlare eine `.zip`-Datei mit folgenden Dateien:

| Datei | Beschreibung |
| --- | --- |
| `dockflare_config.dat` | Verschlüsselter Konfigurations-Payload (Cloudflare-Zugangsdaten, UI-Passwort-Hash, Tunnel-Defaults, Master-API-Key usw.). |
| `dockflare.key` | Fernet-Schlüssel zum Entschlüsseln von `dockflare_config.dat` und anderen verschlüsselten Payloads. Bewahren Sie ihn zusammen mit dem Archiv auf. |
| `agent_keys.dat` | Verschlüsseltes Register der Agent-API-Keys inkl. Metadaten und Widerrufsstatus. |
| `state.json` | Unverschlüsselter JSON-Snapshot des Laufzeitstatus (verwaltete Regeln, Agents, Access Groups). Zum Prüfen oder für gezielte Migration einzelner Teile. |
| `manifest.json` | Checksummen und Versionsinformationen für jede Datei im Archiv. |

Das Backup ist in sich geschlossen: Eine Wiederherstellung über Wizard/Upload schreibt die Dateien nach `/app/data/` und plant sofort einen Container-Neustart, damit die verschlüsselte Konfiguration beim Boot geladen wird.

### Wiederherstellung und Kompatibilität

- **Wizard & Settings UI**: Laden Sie die `.zip` hoch. DockFlare importiert sie, lädt den Status neu und beendet sich. Docker startet den Container automatisch neu, sodass Sie ohne manuelle Schritte wieder im Betriebsmodus sind.
- **Legacy `state.json`**: Für Troubleshooting oder fortgeschrittene Workflows können Sie weiterhin nur eine `state.json` hochladen. DockFlare übernimmt dann nur den Laufzeitstatus und lässt die verschlüsselte Konfiguration aus; Zugangsdaten müssen anschließend erneut eingegeben werden.
- **Automatisierung**: Da der Neustart automatisch erfolgt, sollten Reverse-Proxy-Healthchecks ein kurzes Restart-Fenster (ca. 5 s) nach einer Wiederherstellung tolerieren.

Backups enthalten **nicht** das Redis-Dataset; Redis ist nur Cache. Kritisch ist das `/app/data`-Volume zusammen mit dem Archiv.
