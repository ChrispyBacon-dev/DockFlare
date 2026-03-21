# Schnellstart (Docker Compose)

Diese Anleitung zeigt den schnellsten Weg, um DockFlare mit dem gehärteten Socket-Proxy und der rootless Master-Konfiguration auszuführen.

## Option A — Einzeiliges Installations-Skript (Empfohlen)

Der schnellste Weg, DockFlare zum Laufen zu bringen, ist das Installations-Skript unter [dockflare.app](https://dockflare.app):

```bash
curl -fsSL https://dockflare.app/install.sh | bash
```

Das Skript führt folgende Schritte durch:
1. Prüft, ob Docker und Docker Compose verfügbar sind.
2. Erstellt `~/dockflare/` und schreibt dort eine `docker-compose.yml`.
3. Erstellt das Docker-Netzwerk `cloudflare-net`, falls es noch nicht existiert.
4. Lädt die Images herunter und startet alle Dienste.
5. Gibt die lokale URL aus, wenn fertig.

Nach dem Start öffnen Sie `http://<your-server-ip>:5000` und schließen Sie den Einrichtungsassistenten ab.

> **Optionale Überschreibungen** — Setzen Sie Umgebungsvariablen vor dem Ausführen, um die Installation anzupassen:
> ```bash
> DOCKFLARE_PORT=8080 DOCKFLARE_DIR=/opt/dockflare curl -fsSL https://dockflare.app/install.sh | bash
> ```

---

## Option B — Manuelle Docker-Compose-Einrichtung

### 1. Erstellen Sie die Datei `docker-compose.yml`

Der folgende Stack startet den docker-socket-proxy, richtet das persistente Volume mit den korrekten Berechtigungen ein und startet DockFlare zusammen mit Redis.

```yaml
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
- Der Master-Container läuft als Benutzer `dockflare` (UID/GID 65532). Wenn Sie abweichende Host-Berechtigungen abgleichen müssen, setzen Sie `DOCKFLARE_UID`/`DOCKFLARE_GID` und bauen Sie das Image neu oder passen Sie den Init-Job an.
- Der Proxy ist zwingend erforderlich. DockFlare mountet `/var/run/docker.sock` niemals direkt, was die von dem Master erreichbare Docker API-Fläche streng limitiert.
- Wenn Sie statt benannter Volumes (`named volumes`) Bind-Mounts verwenden, stellen Sie sicher, dass das Zielverzeichnis von UID/GID 65532 (oder Ihren überschriebenen Werten) beschreibbar ist.
- Erstellen Sie das externe Netzwerk einmalig, falls es noch nicht existiert: `docker network create cloudflare-net`.

### 2. Externes Netzwerk erstellen

Falls es noch nicht existiert:

```bash
docker network create cloudflare-net
```

### 3. DockFlare ausführen

Starten Sie den Stack im Detached-Modus (Hintergrund):

```bash
docker compose up -d
```

Dies fährt den Proxy hoch, richtet die Volumes ein und startet DockFlare zusammen mit Redis.

### 4. Schließen Sie die Ersteinrichtung ab

Nachdem die Dienste gestartet sind, öffnen Sie in Ihrem Browser `http://<your-server-ip>:5000`.

Der **Assistent für die Ersteinrichtung** führt Sie durch:
1. Erstellung eines Passworts für die Web-UI.
2. Eingabe Ihrer Cloudflare-Anmeldedaten (Account ID, Zone ID, API Token).
3. Konfiguration Ihres initialen Cloudflare Tunnels.
4. *(Optional)* Wiederherstellung aus einem DockFlare-Backuparchiv. Wenn Sie bereits eine `dockflare_backup_*.zip` besitzen, wählen Sie vor Schritt 1 **Restore from backup** aus; der Assistent importiert Ihre Konfiguration und startet den Container automatisch neu.

### 5. Für bestehende Benutzer (Upgrades)

Wenn Sie ein Upgrade von einer älteren Version durchführen, erkennt DockFlare die alte `.env`-Datei, migriert Ihre Konfiguration in den verschlüsselten Speicher und führt Sie durch die Passworterstellung. Belassen Sie den Socket-Proxy unverändert – direkte Mounts von `/var/run/docker.sock` werden nicht länger unterstützt.
