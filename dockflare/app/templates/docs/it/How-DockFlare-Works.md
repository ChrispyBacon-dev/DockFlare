# Come funziona DockFlare

DockFlare funge da ponte tra il tuo ambiente Docker e la rete Cloudflare, automatizzando il processo di esposizione sicura dei servizi su Internet. Monitora continuamente il tuo host Docker e utilizza l'API Cloudflare per gestire tunnel, record DNS e policy di accesso per tuo conto.

## Flusso di lavoro principale

Il flusso di lavoro principale può essere suddiviso in alcuni passaggi chiave:

1. **Monitoraggio eventi Docker**: DockFlare ascolta gli eventi socket Docker, come `start` e `stop` per i contenitori.

2. **Rilevamento etichette**: quando viene avviato un nuovo contenitore, DockFlare lo controlla per le etichette `dockflare.`. Se un contenitore ha `dockflare.enable=true`, DockFlare sa che deve gestirlo.

3. **Interazione API Cloudflare**: in base alle etichette, DockFlare comunica con l'API Cloudflare per configurare le risorse necessarie:
    * **Tunnel Cloudflare**: aggiunge una regola ingress al tunnel Cloudflare designato. Questa regola instrada il nome host pubblico all'indirizzo di rete interno del container (ad esempio, `http://my-app:8080`).
    * **Gestione DNS**: crea un record DNS CNAME nella tua zona DNS Cloudflare, indirizzando il nome host pubblico desiderato (ad esempio, `my-app.example.com`) al tuo tunnel Cloudflare.
    * **Politiche di accesso**: se hai specificato etichette di controllo dell'accesso, DockFlare crea o aggiorna una politica di accesso Cloudflare riutilizzabile per proteggere il tuo servizio con regole Zero Trust (ad esempio, richiedendo un accesso dal tuo provider di identità o emettendo un `bypass` pubblico).

4. **Pulizia automatica**: quando un container gestito viene arrestato o rimosso, DockFlare attiva automaticamente un processo di pulizia. Rimuove la regola ingress corrispondente dal tunnel Cloudflare e, se nessun altro servizio utilizza il nome host, elimina il record DNS e l'applicazione di accesso. Ciò impedisce record obsoleti e mantiene pulita la configurazione di Cloudflare.


## Componenti in breve

| Componente | Responsabilità |
| --- | --- |
| DockFlare Master | Ospita l'interfaccia web e l'API, monitora gli eventi Docker e orchestra tunnel Cloudflare, DNS e policy di accesso. Funziona senza root e comunica con Docker solo tramite il proxy socket. |
| Proxy socket Docker | Sidecar `tecnativa/docker-socket-proxy` che espone la superficie minima dell'API Docker (`containers`, `events` e così via) al Master. Impedisce al Master di esporre direttamente il socket Docker. |
| Redis | Caching, code, streaming di log e heartbeat/backchannel dell'agente. Vive sulla rete privata `dockflare-internal`. |
| Agenti DockFlare (opzionale) | Worker remoti che rispecchiano il comportamento del Master su altri host, trasmettendo in streaming gli eventi Docker e gestendo i propri `cloudflared`. |
| cloudflared | Mantiene la connessione tunnel a Cloudflare per il Master o ciascun agente. |

## Modello di configurazione a più livelli

DockFlare utilizza un approccio flessibile e stratificato alla configurazione, offrendoti sia l'automazione che il controllo capillare:

1. **Etichette Docker (livello base)**: questo è il metodo automatizzato principale. Puoi definire l'intera configurazione di un servizio (nome host, URL del servizio interno e policy di accesso) direttamente nel comando `docker-compose.yml` o Docker run. Questa è la "fonte della verità" per i servizi automatizzati.

2. **Gruppi di accesso (livello di astrazione)**: per evitare di ripetere policy di accesso complesse su più servizi, è possibile creare **Gruppi di accesso** riutilizzabili nell'interfaccia web. Si tratta di modelli che raggruppano una serie di regole di accesso, ad esempio "consenti email aziendali" o "consenti accesso da paesi specifici", e si sincronizzano con policy di accesso Cloudflare riutilizzabili. L'interruttore Pubblico/Autenticato controlla se DockFlare emette una decisione `bypass` o `allow`. Puoi quindi applicare un'intera policy a un container con una singola etichetta (`dockflare.access.group=my-policy-group`), semplificando notevolmente la configurazione.

3. **Sostituzioni dell'interfaccia web (livello di controllo)**: l'interfaccia web fornisce il massimo livello di controllo. Dalla dashboard puoi:
    * **Sostituire** la policy di accesso di qualsiasi servizio, indipendentemente dal fatto che sia stato definito da etichette o da un gruppo di accesso. Queste sostituzioni sono persistenti e non verranno annullate dal riavvio del container.
    * **Creare regole ingress manuali** per i servizi che non sono in esecuzione in Docker (ad esempio, un servizio su un altro computer nella tua rete).
    * **Ripristinare** la configurazione di un servizio a quanto definito nelle etichette Docker, eliminando eventuali sostituzioni dell'interfaccia web.

Questo modello a più livelli ti consente di automatizzare la maggior parte dei servizi tramite etichette Docker, mantenendo comunque la possibilità di gestire eccezioni e scenari complessi dall'interfaccia web.

---

## Architettura delle policy di accesso (v3.0.3+)

### Sistema di policy riutilizzabile

DockFlare ora utilizza un'**architettura di policy riutilizzabile** in linea con le migliori pratiche di Cloudflare:

1. **Accedi ai gruppi** → Sincronizza con → **Policy riutilizzabili di Cloudflare**
2. **Accesso alle applicazioni** → Riferimento → **ID policy riutilizzabili**
3. **Un'unica fonte di verità**: aggiornamento una volta, applicabile ovunque

Questa architettura elimina la duplicazione delle policy e ti consente di gestire le policy da DockFlare o dalla dashboard di Cloudflare con sincronizzazione bidirezionale completa.

### Policy gestite dal sistema

DockFlare gestisce automaticamente due policy principali per coerenza:

- **`public-default-bypass`**: criterio di bypass dell'accesso pubblico
  - Politica di sistema non cancellabile
  - Creato automaticamente durante l'inizializzazione
  - Nome Cloudflare: `DockFlare-Default-Public-Access-Bypass`
  - Decisione: `bypass` con `everyone` regola di inclusione
  - Utilizzato da tutti i servizi che richiedono accesso pubblico con esclusione della protezione di zona
  - Previene la duplicazione delle policy di bypass nella dashboard di Cloudflare

- **`authenticated-default`**: criterio di autenticazione predefinito
  - Politica di sistema non cancellabile
  - Creato automaticamente durante l'inizializzazione
  - Nome Cloudflare: `DockFlare-Default-Authenticated-Access`
  - Decisione: `allow` con PIN una tantum + limitazione e-mail
  - Utilizzato per scenari di accesso autenticato di base

### Migrazione delle etichette legacy

DockFlare migra automaticamente le etichette legacy per utilizzare le policy di sistema:

- `dockflare.access.policy=bypass` → Utilizza `public-default-bypass`
- `dockflare.access.group=bypass` → Utilizza `public-default-bypass`
- `dockflare.access.policy=authenticate` → Utilizza `authenticated-default`

La migrazione avviene in modo trasparente durante l'elaborazione e la riconciliazione del contenitore. Nessun intervento manuale richiesto.

### Politiche predefinite della zona

Le policy con wildcard a livello di zona (`*.domain.com`) forniscono sicurezza a più livelli attraverso la priorità delle policy:

1. **Politica specifica del nome host** (ad esempio, `app.example.com`) - Priorità più alta
2. **Policy wildcard di zona** (ad esempio, `*.example.com`) - Fallback
3. **Nessuna policy** = Accesso pubblico (nessuna app di accesso) - Impostazione predefinita

Ciò garantisce che i servizi dimenticati o non documentati siano ancora protetti dalla politica a livello di zona, agendo come una rete di sicurezza.

**Esempio:**
- Politica di zona: `*.internal.company.com` → Richiede l'autenticazione e-mail aziendale
- Servizio specifico: `public-demo.internal.company.com` → Utilizza `public-default-bypass`
- Servizio dimenticato: `test.internal.company.com` → Protetto dalla policy di zona (richiede autenticazione)
