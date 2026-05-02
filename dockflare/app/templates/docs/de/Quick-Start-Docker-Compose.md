# Schnellstart (Docker Compose)

Diese Anleitung zeigt den schnellsten Weg, um DockFlare mit dem gehärteten Socket-Proxy und der rootless Master-Konfiguration auszuführen.

## Option A — Einzeiliges Installations-Skript (Empfohlen)

Der schnellste Weg, DockFlare zum Laufen zu bringen, ist das interaktive Installations-Skript unter [dockflare.app](https://dockflare.app):

```bash
bash <(curl -fsSL https://dockflare.app/install.sh)
```

Das Skript führt Sie durch folgende Schritte:
1. Auswahl des Installationsverzeichnisses (Standard: `~/dockflare/`).
2. Auswahl des lokalen UI-Ports (Standard: `5000`).
3. Optional: Konfiguration eines Cloudflare-Tunnels für DockFlare selbst.
4. Optional: Aktivierung des E-Mail-Profils (dockflare-mail-manager + dockflare-webmail).

Anschließend schreibt es die `docker-compose.yml`, ermöglicht eine Überprüfung und fragt vor dem Starten nach.

Nach dem Start öffnen Sie `http://<your-server-ip>:5000` und schließen Sie den Einrichtungsassistenten ab.

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
    logging:
      driver: "none"
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
    command: ["sh", "-c", "chown -R ${DOCKFLARE_UID:-65532}:${DOCKFLARE_GID:-65532} /app/data"]
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
      - "5000:5000" # Optional: comment out once exposed via Cloudflare Tunnel with an Access Policy to restrict access to tunnel-only
    #labels: # -- Cloudflare Tunnel Configuration (via DockFlare) OPTIONAL --
      # Main DockFlare with access policy
      #- dockflare.enable=true
      #- dockflare.hostname=dockflare.TLD  # replace with your domain
      #- dockflare.service=http://dockflare:5000
      #- dockflare.access.group=YOUR-ACCESS-GROUP-ID  # your custom access policy
      # -- OAuth Callback Path (Bypass Access Policy) OPTIONAL --
      # Required if using OAuth authentication with access policies on main interface
      #- dockflare.0.hostname=dockflare.example.tld
      #- dockflare.0.path=/auth/google/callback
      #- dockflare.0.service=http://dockflare:5000
      #- dockflare.0.access.group=public-default-bypass

      # Add additional callback paths for other OAuth providers as needed
      # - dockflare.1.hostname=dockflare.example.com
      # - dockflare.1.path=/auth/github/callback
      # - dockflare.1.service=http://dockflare:5000
      # - dockflare.1.access.group=public-default-bypass
    volumes:
      - dockflare_data:/app/data
    environment:
      - REDIS_URL=redis://redis:6379/0
      - REDIS_DB_INDEX=0
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
    logging:
      driver: "none"
    volumes:
      - dockflare_redis:/data
    networks:
      - dockflare-internal

  dockflare-mail-manager:
    image: alplat/dockflare-mail-manager:stable
    container_name: dockflare-mail-manager
    restart: unless-stopped
    profiles: ["email"]
    environment:
      - DOCKFLARE_MASTER_URL=http://dockflare:5000
      - MAIL_DATA_PATH=/data
    volumes:
      - mail_data:/data
    depends_on:
      dockflare:
        condition: service_started
    networks:
      - cloudflare-net
      - dockflare-internal

  dockflare-webmail:
    image: alplat/dockflare-webmail:stable
    container_name: dockflare-webmail
    restart: unless-stopped
    profiles: ["email"]
    environment:
      - DOCKFLARE_MASTER_URL=https://dockflare.TLD  # replace with your domain
    labels:
      - dockflare.enable=true
      - dockflare.hostname=mail.dockflare.TLD  # replace with your domain
      - dockflare.service=http://dockflare-webmail:80
    depends_on:
      dockflare-mail-manager:
        condition: service_started
    networks:
      - cloudflare-net
      - dockflare-internal

volumes:
  dockflare_data:
  dockflare_redis:
  mail_data:

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
