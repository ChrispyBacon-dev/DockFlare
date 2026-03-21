# Schnällstart mit Docker Compose

Die Aaleitig zeigt dr schnäuschti Wäg, wie du DockFlare mit em ghärtete Socket-Proxy u dr rootless Master-Konfiguration lafe lahsch.

## Option A — Eizeiler-Installation (Empfohle)

Dr schnäuschti Wäg, DockFlare zum Laufe z bringe, isch dr Installations-Skript uf [dockflare.app](https://dockflare.app):

```bash
curl -fsSL https://dockflare.app/install.sh | bash
```

Dr Skript macht Folgendes:
1. Prüeft, ob Docker u Docker Compose verfüegbar si.
2. Erstellt `~/dockflare/` u schrybt dort e `docker-compose.yml` ane.
3. Erstellt s Docker-Netzwerk `cloudflare-net`, falls's no nid existiert.
4. Ladet d Images abe u startet alli Dienscht.
5. Zeigt d lokali URL aa, wenn's fertig isch.

Sobald alles lauft, mach `http://<your-server-ip>:5000` uf u füehrt di dr Iirichtigsassistent dür.

> **Optionali Yberschribige** — setz Umgebigsvariable vor em Pipe, zum d Installation aapasse:
> ```bash
> DOCKFLARE_PORT=8080 DOCKFLARE_DIR=/opt/dockflare curl -fsSL https://dockflare.app/install.sh | bash
> ```

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
