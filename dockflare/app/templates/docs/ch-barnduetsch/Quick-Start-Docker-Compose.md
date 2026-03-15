# Schnellstart (Docker Compose)

Diese Aaleitig zeigt den schnellsten Weg, um DockFlare mit dem gehärteten Socket-Proxy u der rootless Master-Konfiguration auszuführen.

### 1. Erstell die Datei `docker-compose.yml`

Der folgende Stack startet den docker-socket-proxy, richtet das persistente Volume mit den korrekten Berechtigungen ein u startet DockFlare zusammen mit Redis.

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

**Hinweise:**
- Der Master-Container läuft als Benutzer `dockflare` (UID/GID 65532). Wänn du abweichendi Host-Berechtige abgliiche muesch, setz `DOCKFLARE_UID`/`DOCKFLARE_GID` u bau s'Image neu oder pass den Init-Job a.
- Der Proxy isch zwingend nötig. DockFlare mountet `/var/run/docker.sock` niemals direkt, was die von dem Master erreichbare Docker API-Fläche streng limitiert.
- Wänn du statt benannter Volumes (`named volumes`) Bind-Mounts bruuche, lueg dass das Zielverzeichnis von UID/GID 65532 (oder dini überschriebenen Werten) beschreibbar isch.
- Erstell das externe Netzwerk einmalig, falls es noch nid existiert: `docker network create cloudflare-net`.

### 2. DockFlare ausführen

Start den Stack im Detached-Modus (Hintergrund):

```bash
docker compose up -d
```

Das fährt den Proxy hoch, richtet die Volumes ein u startet DockFlare zusammen mit Redis.

### 3. Schliess d'Erstiirichtig ab

Nachdem die Dienste gestartet si, mach uf in dim Browser `http://<your-server-ip>:5000`.

Der **Assistent für d'Erstiirichtig** führt di durch:
1. Erstellung eines Passworts für die Web UI.
2. Eingabe dinere Cloudflare-Anmeldedaten (Account ID, Zone ID, API Token).
3. Konfiguration din initialen Cloudflare Tunnels.
4. *(Optional)* Wiederherstellung us eme DockFlare-Backuparchiv. Wänn du scho e `dockflare_backup_*.zip` hesch, wähl vor Schritt 1 **Restore from backup** us; dr Assistent importiert dini Konfiguration u startet dr Container automatisch neu.

### 4. Für bestehende Benutzer (Upgrades)

Wänn du es Upgrade vo ere ältere Version machsch, erkennt DockFlare d'alti `.env`-Datei, migriert dini Konfiguration i dr verschlüsslete Speicher u führt di durch d'Passworterstellung. Lah dr Socket-Proxy unverändert; direkti Mounts vo `/var/run/docker.sock` wärde nid länger unterstützt.
