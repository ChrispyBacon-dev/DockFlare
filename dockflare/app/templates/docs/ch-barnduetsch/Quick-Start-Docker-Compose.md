# Schnällstart mit Docker Compose

Die Aaleitig zeigt dr schnäuschti Wäg, wie du DockFlare mit em ghärtete Socket-Proxy u dr rootless Master-Konfiguration lafe lahsch.

## Option A — Eizeiler-Installation (Empfohle)

Dr schnäuschti Wäg, DockFlare zum Laufe z bringe, isch dr interaktivi Installations-Skript uf [dockflare.app](https://dockflare.app):

```bash
bash <(curl -fsSL https://dockflare.app/install.sh)
```

Dr Skript füehrt di dür folgende Schritt:
1. Uswahl vom Installationsverzeuchnis (Standard: `~/dockflare/`).
2. Uswahl vom lokale UI-Port (Standard: `5000`).
3. Optionali Konfiguration vomene Cloudflare-Tunnel für DockFlare.
4. Optionali Aktivierig vom E-Mail-Profil (dockflare-mail-manager + dockflare-webmail).

Dernoo schrybt er d `docker-compose.yml`, lot di se aaluege u fragt vor em Starte nochmal nach.

Sobald alles lauft, mach `http://<your-server-ip>:5000` uf u füehrt di dr Iirichtigsassistent dür.

---

## Option B — Manuälli Docker-Compose-Irichtig

### 1. Erstell e `docker-compose.yml`

Dr folgend Stack startet dr `docker-socket-proxy`, macht s persistänte Volume mit de richtige Rächt parat u startet DockFlare zäme mit Redis.

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

**Wichtig:**
- Dr Master-Container lauft als Benutzer `dockflare` (UID/GID 65532). Wänn du anderi Host-Rächt hesch, setz `DOCKFLARE_UID`/`DOCKFLARE_GID` u bou s Image neu oder pass dr Init-Job aa.
- Dr Proxy isch Pflicht. DockFlare mountet `/var/run/docker.sock` nie direkt, damit d Docker-API-Flächi möglichst chli blybt.
- Wänn du statt named Volumes Bind-Mounts bruuchsch, mues s Zielverzeichnis für UID/GID 65532 beschrybbar si.
- Dr externi Network `cloudflare-net` mues nume einisch erstellt wärde: `docker network create cloudflare-net`.

### 2. S externe Netzwerk erstelle

Falls's no nid existiert:

```bash
docker network create cloudflare-net
```

### 3. DockFlare starte

Start dr Stack im Hintergrund:

```bash
docker compose up -d
```

Dä Befehl fährt dr Proxy u Redis hoch u startet nachhär DockFlare.

### 4. Erstiirichtig abschliesse

Sobald d Dienscht laufe, mach im Browser `http://<your-server-ip>:5000` uf.

Dr **Erstiirichtigs-Assistent** füehrt di dür:
1. es Passwort für d Web UI setze
2. Cloudflare-Daten iitrage (`Account ID`, `Zone ID`, `API Token`)
3. dr erscht Tunnel konfiguriere
4. optional es bestehends `dockflare_backup_*.zip` wiederherstelle

### 5. Upgrade vo ältere Versione

Wänn du vo nere ältere Version upgradisch, erkennt DockFlare d alti `.env`, migriert dini Konfiguration i dr verschlüsslete Speicher u füehrt di dür d Passwort-Erstellige. Lah dr Socket-Proxy unveränderet; diräkti Mounts vo `/var/run/docker.sock` wärde nüm unterstützt.
