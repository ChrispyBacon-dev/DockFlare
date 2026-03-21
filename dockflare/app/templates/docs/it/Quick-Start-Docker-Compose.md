# Avvio rapido (Docker Compose)

Questa guida illustra il modo più veloce per eseguire DockFlare con un `docker-socket-proxy` rinforzato e una configurazione Master rootless.

## Opzione A — Installazione con un solo comando (Consigliato)

Il modo più rapido per avviare DockFlare è lo script di installazione disponibile su [dockflare.app](https://dockflare.app):

```bash
curl -fsSL https://dockflare.app/install.sh | bash
```

Lo script eseguirà le seguenti operazioni:
1. Verificare che Docker e Docker Compose siano disponibili.
2. Creare `~/dockflare/` e scrivere un file `docker-compose.yml` al suo interno.
3. Creare la rete Docker `cloudflare-net` se non esiste ancora.
4. Scaricare le immagini e avviare tutti i servizi.
5. Stampare l'URL locale al termine.

Una volta avviato, apri `http://<your-server-ip>:5000` e completa la procedura guidata di configurazione.

> **Sostituzioni opzionali** — imposta le variabili d'ambiente prima del pipe per controllare l'installazione:
> ```bash
> DOCKFLARE_PORT=8080 DOCKFLARE_DIR=/opt/dockflare curl -fsSL https://dockflare.app/install.sh | bash
> ```

---

## Opzione B — Docker Compose manuale

### 1. Crea il file `docker-compose.yml`

Lo stack seguente avvia `docker-socket-proxy`, imposta i permessi corretti sul volume persistente e avvia DockFlare insieme a Redis.

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

**Note:**
- Il container DockFlare (Master) viene eseguito come utente `dockflare` (UID/GID 65532). Se devi allineare permessi diversi lato host, imposta `DOCKFLARE_UID`/`DOCKFLARE_GID` e ricostruisci l'immagine oppure modifica il job di init.
- Il proxy è obbligatorio. DockFlare non monta mai direttamente `/var/run/docker.sock`, limitando la superficie dell'API Docker a cui il Master può accedere.
- Se usi bind mount invece dei volumi nominati, assicurati che la directory di destinazione sia scrivibile da UID/GID 65532 (o dai valori sovrascritti).
- Crea una volta la rete esterna se non esiste: `docker network create cloudflare-net`.

### 2. Crea la rete esterna

Se non esiste ancora:

```bash
docker network create cloudflare-net
```

### 3. Esegui DockFlare

Avvia lo stack in modalità distaccata:

```bash
docker compose up -d
```

Questo avvia il proxy, prepara il volume e lancia DockFlare insieme a Redis.

### 4. Completa la configurazione iniziale

Una volta eseguiti i servizi, apri il browser su `http://<your-server-ip>:5000`.

L'**assistente di configurazione iniziale** ti guida attraverso:
1. Creazione di una password per l'interfaccia web.
2. Immissione delle credenziali Cloudflare (ID account, ID zona, token API).
3. Configurazione del tuo tunnel Cloudflare iniziale.
4. *(Facoltativo)* Ripristino da un archivio di backup DockFlare. Se hai già un `dockflare_backup_*.zip`, scegli **Ripristina da backup** prima del Passaggio 1; la procedura guidata importa la configurazione e riavvia automaticamente il contenitore.

### 5. Per gli utenti esistenti (aggiornamento)

Se stai effettuando l'aggiornamento da una versione precedente, DockFlare rileva il file `.env` legacy, migra la tua configurazione nell'archivio crittografato e ti guida attraverso la creazione della password. Mantieni il proxy socket in posizione: i montaggi diretti di `/var/run/docker.sock` non sono più supportati.
