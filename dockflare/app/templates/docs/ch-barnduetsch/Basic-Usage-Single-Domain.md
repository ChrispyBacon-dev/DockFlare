# Grundlag vom Bruuch (einzeli Domain)

Da Leitfade zeigt dr tüüpschti Use Case: E einzelne Docker-Container über en öffentliche Hostname erreichbar mache.

## Voraussetzige

Bevor du afahsch:
1. Du hesch dr [Schnällstart](Quick-Start-Docker-Compose.md) gmacht.
2. DockFlare lauft u isch mit Cloudflare verbunde.
3. Du hesch e Dienst, wo du wotsch veröffentliche.

## Beispiel: Freigabe eines NGINX-Containers

Näh mer aa, du wotsch en NGINX-Webserver under `nginx.example.com` laufe lah.

### 1. Dienst i dini `docker-compose.yml` iiträge

Dr wichtigschti Teil si d `dockflare.*`-Labels am Dienst.

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
> **Warum Redis?** DockFlare bruucht Redis für Cache, Log-Streaming u d Kommunikation zwüsche Komponente. Im private Network `dockflare-internal` blybt Redis vo de Workloads trennt.

### 2. Was d Labels bedüte

* `dockflare.enable=true`: DockFlare söll dä Container verwalte.
* `dockflare.hostname=nginx.example.com`: Das isch dr öffentliche Hostname.
* `dockflare.service=http://nginx-webserver:80`: Da geit dr Tunnel intern häre.
* `dockflare.access.group=public-default-bypass`: Optional für öffentliche Zugäng mit Bypass.

### 3. Dienst starte

Speicher dini `docker-compose.yml` u start dr Stack:

```bash
docker compose up -d
```

### 4. Prüefe

DockFlare erkennt dr neu Container u macht automatisch:
1. e Ingress-Regel für `nginx.example.com`
2. e CNAME-Iitrag i Cloudflare

Prüefe chasch s so:
* **DockFlare Web UI:** `nginx.example.com` erscheint im Dashboard
* **Cloudflare Dashboard:** Dr CNAME-Iitrag u d Tunnel-Route si sichtbar

Nach ere churze DNS-Propagation söttsch `https://nginx.example.com` im Browser chönne ufmache.


## Backup & Wiederherstellung im Detail

DockFlare het en integrierte Backup-Flow, mit däm du e Instanz schnäu migriere oder wiederherstelle chasch.

### Was im Backup-Archiv drin isch

Wänn du under **Settings -> Backup & Restore** es Backup abeladsch, bechunsch e `.zip` mit dene Date:

| Datei | Beschreibung |
| --- | --- |
| `dockflare_config.dat` | Verschlüsselter Konfigurations-Payload (Cloudflare-Zugangsdaten, UI-Passwort-Hash, Tunnel-Defaults, Master-API-Key usw.). |
| `dockflare.key` | Fernet-Schlüssel zum Entschlüsseln von `dockflare_config.dat` u anderen verschlüsselten Payloads. Bhalt ihn zusammen mit dem Archiv auf. |
| `agent_keys.dat` | Verschlüsseltes Register der Agent-API-Keys inkl. Metadaten u Widerrufsstatus. |
| `state.json` | Unverschlüsselter JSON-Snapshot des Laufzeitstatus (verwaltete Regeln, Agents, Access Groups). Zum Prüfen oder für gezielte Migration einzelner Teile. |
| `manifest.json` | Checksummen u Versionsinformationen für jede Datei im Archiv. |

Das Backup isch sich sälber gnueg: Bi dr Wiederherstellig wärde d Date nach `/app/data/` zrügggschribe u dr Container startet automatisch neu.

### Wiederherstellig u Kompatibilität

- **Wizard u Settings UI:** `.zip` ufelade, importiere lah, fertig.
- **Legacy `state.json`:** Für Troubleshooting geit o nume `state.json`, aber Zugangsdaten wärde nid wiederhärgstellt.
- **Automatische Neustarts:** Health Checks söue churzi Restart-Fänschter vertrage.

Im Backup isch **nid** s Redis-Dataset drin, wiu Redis nume Cache isch. Kritisch isch `/app/data` plus dis Backup-Archiv.
