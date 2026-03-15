# Utilizzo di base (dominio singolo)

Questa guida illustra il caso d'uso più comune per DockFlare: esporre un singolo contenitore Docker a Internet su un nome host pubblico.

## Prerequisiti

Prima di iniziare, assicurati di avere:
1. Completata la guida [Avvio rapido](Quick-Start-Docker-Compose.md).
2. DockFlare è in esecuzione e connesso al tuo account Cloudflare.
3. Hai un servizio che desideri esporre (in questo esempio utilizzeremo `nginx`).

## Esempio: esposizione di un contenitore NGINX

Supponiamo che tu voglia esporre un server web NGINX standard con il nome host `nginx.example.com`.

### 1. Aggiungi il servizio al tuo `docker-compose.yml`

Modifica il tuo file `docker-compose.yml` per includere il servizio `nginx`. La chiave è aggiungere le etichette `dockflare.*` alla sua configurazione.

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
> **Perché Redis?** DockFlare si affida a Redis per la memorizzazione nella cache, lo streaming dei log e la messaggistica cross-thread. L'esecuzione sulla rete privata `dockflare-internal` mantiene Redis raggiungibile solo da DockFlare, mentre i carichi di lavoro rimangono isolati su `cloudflare-net`.


### 2. Comprendere le etichette

* `dockflare.enable=true`: questo dice a DockFlare di gestire questo contenitore.
* `dockflare.hostname=nginx.example.com`: questo è l'URL pubblico in cui sarà disponibile il tuo servizio. DockFlare creerà un record DNS per questo nome host nel tuo account Cloudflare.
* `dockflare.service=http://nginx-webserver:80`: indica a Cloudflare Tunnel dove inviare il traffico. È l'indirizzo interno del container NGINX. Tieni presente che stiamo utilizzando il nome del servizio (`nginx-webserver`) come hostname: funziona perché entrambi i container si trovano sulla stessa rete Docker.
* `dockflare.access.group=public-default-bypass`: (facoltativo) utilizza la policy di bypass del sistema per garantire l'accesso pubblico anche se esiste una policy di protezione `*.example.com` a livello di zona. Questo è importante quando disponi di policy con wildcard che proteggono il tuo dominio ma hai bisogno che servizi specifici rimangano pubblici.

### 3. Distribuire il servizio

Salva il tuo file `docker-compose.yml` ed esegui il comando seguente per avviare il nuovo servizio:

```bash
docker compose up -d
```

### 4. Verifica

DockFlare rileverà il nuovo contenitore ed eseguirà automaticamente le seguenti azioni:
1. Aggiungi una regola ingress al tuo Cloudflare Tunnel per `nginx.example.com`.
2. Crea un record CNAME per `nginx.example.com` nel tuo DNS Cloudflare, puntando al tunnel.

Puoi verificarlo in alcuni modi:
* **Interfaccia web di DockFlare**: il servizio `nginx.example.com` apparirà sulla dashboard.
* **Dashboard di Cloudflare**: vedrai il nuovo record CNAME nelle tue impostazioni DNS e la nuova regola ingress nella configurazione del tunnel.

Dopo alcuni istanti necessari per la propagazione del DNS, dovresti essere in grado di accedere a `https://nginx.example.com` nel tuo browser e visualizzare la pagina di benvenuto NGINX predefinita.

## Approfondimento: backup e ripristino

DockFlare viene fornito con un flusso di backup di prima classe che ti consente di spostare o ripristinare un'istanza in pochi minuti.

### Cosa contiene l'archivio di backup

Quando scarichi un backup da **Impostazioni → Backup e ripristino** (o dalla procedura guidata di onboarding), DockFlare genera un `.zip` con i seguenti file:

| File | Descrizione |
| --- | --- |
| `dockflare_config.dat` | Payload di configurazione crittografato (credenziali Cloudflare, hash della password dell'interfaccia utente, impostazioni predefinite del tunnel, chiave API principale, ecc.). |
| `dockflare.key` | La chiave Fernet utilizzata per decrittografare `dockflare_config.dat` e altri payload crittografati. Conservalo nell'archivio. |
| `agent_keys.dat` | Registro crittografato delle chiavi API dell'agente, dei metadati e dello stato di revoca. |
| `state.json` | Semplice istantanea JSON dello stato di runtime: regole gestite, agenti, gruppi di accesso. Questo è incluso in modo che gli operatori possano ispezionare o migrare pezzi specifici, se necessario. |
| `manifest.json` | Checksum e informazioni sulle versioni per ogni file nell'archivio. |

Il backup è autonomo: ripristinandolo tramite la procedura guidata/applica endpoint scrive ogni file su `/app/data/` e pianifica immediatamente un riavvio del contenitore in modo che la configurazione crittografata venga ricaricata all'avvio.

### Note sul ripristino e sulla compatibilità

- **Interfaccia utente guidata e impostazioni**: carica `.zip` e DockFlare lo importerà, ricaricherà lo stato e uscirà. Docker riavvia automaticamente il container, così torni in modalità operativa senza intervento manuale.
- **Legacy `state.json`**: per la risoluzione dei problemi o flussi di lavoro avanzati puoi comunque caricare solo un file `state.json`. DockFlare popolerà lo stato di runtime da esso ma salterà la configurazione crittografata; successivamente sarà necessario reinserire le credenziali.
- **Automazione**: poiché il riavvio è automatico, assicurati che eventuali controlli di integrità del proxy inverso consentano una breve finestra di riavvio (~ 5 secondi) dopo un ripristino.

I backup **non** includono il set di dati Redis; memorizza nella cache solo i dati che DockFlare può ricalcolare. Il volume `/app/data` accanto all'archivio è l'elemento fondamentale da proteggere e sottoporre a backup.
