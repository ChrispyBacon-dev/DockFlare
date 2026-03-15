# Agente DockFlare e architettura multi-server

DockFlare 3.0 introduce un modello di esecuzione distribuita che consente di gestire i tunnel Cloudflare su più host Docker. DockFlare **Master** coordina la configurazione, mentre i leggeri **agenti** vengono eseguiti accanto ai tuoi carichi di lavoro e mantengono sincronizzata la loro istanza locale di `cloudflared` con il Master.

Questa guida spiega l'architettura, il modello di sicurezza e il flusso di lavoro passo passo per la distribuzione degli agenti.

---

## Perché gli agenti?

* **Disaccoppia l'elaborazione dall'ingresso**: mantieni i carichi di lavoro vicini agli utenti mantenendo un unico piano di controllo.
* **Visibilità per host**: monitora heartbeat, stato del tunnel e cronologia dei comandi per ciascun agente.
* **Token con privilegio minimo**: revoca gli agenti compromessi senza toccare il Master o altri host.
* **Aggiornamenti resilienti**: gli agenti continuano a servire il traffico con l'ultima configurazione conosciuta se il Master è temporaneamente non disponibile.

---

## Componenti in breve

| Componente | Responsabilità |
|-----------|----------------|
| **Master (DockFlare)** | Ospita l'interfaccia web, memorizza lo stato, riconcilia le regole ingress desiderate e invia comandi. |
| **Redis** | Livello condiviso per cache, heartbeat dell'agente e comandi in coda. |
| **Agente DockFlare** | Contenitore headless che osserva gli eventi Docker locali, esegue comandi e gestisce `cloudflared`. |
| **cloudflared** | Gestisce la connessione tunnel effettiva a Cloudflare per agente. |

Il Master e Redis vengono generalmente eseguiti insieme, mentre gli agenti vengono eseguiti accanto ai carichi di lavoro (potenzialmente su reti remote).

---

## Prerequisiti

* DockFlare Master ≥ v3.0 con Redis configurato (`REDIS_URL` set). Facoltativamente, specifica `REDIS_DB_INDEX` per isolare i dati da altri contenitori utilizzando la stessa istanza Redis.
* Token API Cloudflare con autorizzazioni Tunnel + Accesso (come le versioni precedenti).
* Runtime Docker su ogni host che intendi gestire.
* (Facoltativo) Segmento di rete dedicato o VPN tra Master e agenti se non esponi pubblicamente il Master.

---

## Panoramica del flusso di lavoro

1. **Genera una chiave API dell'agente** nell'interfaccia web di DockFlare (`Agents → Generate Key`).
2. **Distribuire il contenitore DockFlare Agent** sull'host remoto, passando l'URL principale e la chiave.
3. L'agente **si registra** presso il Master e appare con lo stato *In sospeso*.
4. Dall'interfaccia principale, **approva** l'agente: assegna o crea un tunnel Cloudflare per quell'host.
5. Il Master mette in coda i comandi; l'agente **esegue il polling**, applica la configurazione e segnala lo stato/battito cardiaco. DockFlare rileva automaticamente la zona di destinazione per ciascun nome host (ritornando alla zona predefinita solo quando il rilevamento fallisce).
6. Quando i container vengono avviati/arrestati sull'host dell'agente, l'agente trasmette gli eventi al Master che aggiorna DNS, policy di accesso e regole ingress del tunnel.

---

## Distribuzione dell'agente DockFlare

> ℹ️ L'agente verrà pubblicato come `alplat/dockflare-agent`. Fino a quando il repository pubblico non sarà attivo, puoi creare dall'albero dei sorgenti `DockFlare-agent` incluso con DockFlare 3.0.

```bash
# Example environment file used by the agent container
DOCKFLARE_MASTER_URL=https://dockflare.example.com
DOCKFLARE_API_KEY=agent_api_key_goes_here
DOCKER_HOST=tcp://docker-socket-proxy:2375
# control the docker image used for the managed cloudflared tunnel (accepts repo:tag or repo@sha256:<digest>)
CLOUDFLARED_IMAGE=cloudflare/cloudflared:2025.9.0
LOG_LEVEL=info
TZ=Europe/Zurich
```

`docker-compose.yml` minimo sull'host dell'agente:

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
      - EXEC=1
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock
    networks:
      - dockflare-internal
      
  dockflare-agent:
    image: alplat/dockflare-agent:latest
    container_name: dockflare-agent
    restart: unless-stopped
    env_file:
      - .env
    environment:
      - DOCKER_HOST=${DOCKER_HOST:-tcp://docker-socket-proxy:2375}
      - TZ=${TZ:-UTC}
      - LOG_LEVEL=${LOG_LEVEL:-info}
    volumes:
      - agent_data:/app/data
    depends_on:
      - docker-socket-proxy
    networks:
      - cloudflare-net
      - dockflare-internal

volumes:
  agent_data:

networks:
  cloudflare-net:
    name: cloudflare-net
    external: true
  dockflare-internal:
    name: dockflare-internal
```

- Esegui `docker network create cloudflare-net` una volta per eseguire il provisioning della rete condivisa utilizzata dal Master e dagli agenti.
- Il proxy socket limita la superficie dell'API Docker che l'agente può raggiungere; vengono esposte solo le funzionalità impostate su `1`.
- L'immagine dell'agente viene eseguita come utente `dockflare` non privilegiato (UID/GID 65532). Assicurati che le directory montate come `/app/data` siano scrivibili da quell'account o ricostruiscile con `DOCKFLARE_UID/DOCKFLARE_GID` in modo che corrispondano al tuo host.
- Compilare un file `.env` con `DOCKFLARE_MASTER_URL` e `DOCKFLARE_API_KEY`; le sostituzioni facoltative (ad esempio `LOG_LEVEL` o `DOCKER_HOST`) possono essere fornite allo stesso modo.

---

## Modello di sicurezza

* **Chiave API principale**: protegge l'API amministrativa. L'interfaccia la mostra solo dopo aver fatto clic su *Mostra chiave API principale*.
* **Chiavi API dell'agente**: univoche per agente. La revoca di una chiave blocca immediatamente ulteriori registrazioni/comandi da quell'host.
* **Redis** – utilizzato per code e cache; proteggerlo (password + ACL di rete) se eseguito all'esterno di una LAN attendibile.
* **Trasporto** – esegui il Master dietro HTTPS (ad esempio, tramite Cloudflare Access) in modo che il traffico dell'agente sia crittografato.
* **Runtime con privilegi minimi**: il contenitore dell'agente viene eseguito come utente `dockflare` (UID/GID 65532) e si basa sul proxy socket per mantenere l'accesso Docker limitato all'ispezione del contenitore e al controllo del ciclo di vita.

### Indurimento consigliato

1. Conservare le chiavi dell'agente in un vault/gestore di password; ruotare regolarmente.
2. **Non disabilitare l'accesso tramite password**: utilizza invece i provider OAuth/OIDC per ottenere il single sign-on senza introdurre rischi per la sicurezza. Se è necessario disabilitare l'accesso tramite password, tieni presente che ciò crea una vulnerabilità sulla rete Docker: qualsiasi container sulla stessa rete può ignorare l'autenticazione esterna. Consulta [Accesso all'interfaccia web](Accessing-the-Web-UI.md) per tutte le implicazioni sulla sicurezza.
3. Utilizzare tunnel separati per agente per l'isolamento con privilegi minimi.
4. Monitora la pagina `Agents` per eventuali lacune di heartbeat: i nodi offline possono essere rimossi direttamente dall'interfaccia utente.

---

## Risoluzione dei problemi

| Sintomo | Correzione |
|---------|-----|
| Agente bloccato in `pending` | Assicurati che sia stato registrato con la chiave API corretta e approvalo dall'interfaccia web. |
| I comandi non cancellano mai | Conferma la connettività Redis e che gli orologi del contenitore dell'agente siano sincronizzati. |
| DNS non aggiornato | Il Master deve raggiungere Cloudflare e l'agente deve inviare eventi container; verifica `docker logs dockflare-agent`. |
| Battito cardiaco offline | Controlla il percorso di rete tra agente e Master; i problemi relativi al firewall o al TLS sono cause comuni. |

---

## Passaggi successivi

* Esamina il Quick Start aggiornato nel file README del repository per assicurarti che Redis sia configurato.
* Controlla il registro delle modifiche per eventuali modifiche importanti e note di migrazione.
* Iscriviti al repository pubblico di DockFlare Agent una volta pubblicato per rimanere aggiornato con le versioni.

Buon tunneling! 🚇
