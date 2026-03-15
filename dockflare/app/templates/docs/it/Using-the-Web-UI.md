# Uso della Web UI

La Web UI di DockFlare è uno strumento potente per gestire, monitorare e configurare i tuoi servizi. Offre un'interfaccia comoda per attività che vanno oltre la semplice configurazione delle etichette Docker.

## La dashboard (pagina principale)

La prima pagina che vedi dopo aver effettuato l'accesso è la dashboard principale. Questo è il tuo hub centrale per visualizzare lo stato di tutti i tuoi servizi gestiti.

* **Tabella delle regole ingress gestite:** questa tabella elenca tutte le regole ingress gestite da DockFlare, sia che provengano da un container Docker sia che siano state create manualmente.
    * **Nome host:** il nome host pubblico del servizio.
    * **Servizio:** l'URL di destinazione interno.
    * **Origine:** Indica se la regola proviene da `Docker` o è stata creata `Manually` nell'interfaccia utente.
    * **Stato:** Mostra se la regola è `active`, `pending_deletion` o ha un `UI Override`.
    * **Accesso:** Visualizza il gruppo di accesso applicato e il badge della modalità. Aspettatevi di vedere etichette `Public` o `Authenticated`, nomi di gruppi a cascata e collegamenti rapidi alla dashboard di Cloudflare quando si sincronizzano le policy riutilizzabili.
    * **Gestisci regola:** questo pulsante ti consente di modificare qualsiasi regola.
* **Registri in tempo reale:** sotto la tabella troverai un visualizzatore di registri in tempo reale che trasmette i registri dal backend DockFlare, il che è prezioso per il debug.

## Gestione delle regole

La Web UI ti offre il pieno controllo sulle regole ingress.

* **Aggiungi regola manuale:** Il pulsante "Aggiungi regola manuale" ti consente di creare regole ingress per i servizi che non sono in esecuzione in Docker (ad esempio, un servizio su un altro computer nella tua LAN). Il modulo consente di specificare hostname, URL del servizio e, facoltativamente, di applicare un gruppo di accesso.
* **Modifica qualsiasi regola:** Il pulsante "Gestisci regola" accanto a ogni regola apre una finestra modale in cui puoi modificarne la configurazione. In questo modo puoi applicare una sostituzione dell'interfaccia utente a una regola originariamente creata dalle etichette Docker.
* **Ripristina alle etichette:** se una regola di Docker ha una sostituzione dell'interfaccia utente, verrà visualizzato un pulsante "Ripristina alle etichette", che ti consentirà di ignorare le modifiche manuali e lasciare che la regola venga nuovamente controllata dalle relative etichette Docker.

## Pagina delle policy di accesso

Questa pagina è il punto centrale per gestire i tuoi **Gruppi di accesso** riutilizzabili e proteggere le zone DNS con policy wildcard.

### Politiche di accesso avanzate

Dalla sezione Gruppi di accesso è possibile:
* **Crea** nuovi gruppi di accesso utilizzando il modale a due schede (Autenticato vs Pubblico). I banner di guida si aggiornano per scheda in modo da capire quando DockFlare emetterà una decisione Cloudflare `allow` o `bypass`.
* **Modifica** gruppi di accesso esistenti. La modalità applica la convalida specifica della modalità (e-mail richieste per l'autenticazione) e mantiene visibili le impostazioni Geo/IP per entrambe le modalità.
* **Elimina** i gruppi di accesso che non sono più in uso (le policy di sistema come `public-default-bypass` non possono essere eliminate).
* **Sincronizza da Cloudflare** per importare le policy riutilizzabili DockFlare esistenti dal tuo account.
* Utilizza il menu di azione accanto a ciascuna voce per aprire la policy corrispondente direttamente nel dashboard di Cloudflare tramite il collegamento dell'icona di Cloudflare.

**Nota:** la politica di sistema `public-default-bypass` viene creata e gestita automaticamente da DockFlare. Tutti i servizi che utilizzano l'accesso "Bypass" fanno riferimento a questa singola policy, mantenendo pulita la dashboard di Cloudflare.

### Policy predefinite della zona (wildcard *.tld)

La seconda sezione mostra le **Zone Default Policies**, una funzionalità di best practice di sicurezza che protegge tutti i sottodomini:

* **Stato di protezione:** I badge visivi mostrano quali zone DNS hanno una policy wildcard `*.domain.com` (Protetta 🛡️) e quali no (Non protetta ⚠️).
* **Crea policy di zona:** fare clic su "Crea policy" su qualsiasi zona non protetta per creare un'applicazione di accesso con wildcard.
* **Seleziona policy:** Scegli quale gruppo di accesso deve proteggere tutti i sottodomini della zona (può essere bypass pubblico, autenticazione o qualsiasi policy personalizzata).
* **Rete di sicurezza:** Anche se dimentichi di aggiungere una policy a un servizio specifico, la policy wildcard a livello di zona lo proteggerà comunque.

**Best practice:** crea policy predefinite di zona per tutti i tuoi domini. Per i domini pubblici, utilizza il criterio di bypass predefinito. Per i domini interni/privati, utilizzare una policy di autenticazione. Ciò garantisce che nessun sottodominio venga accidentalmente esposto.

Per ulteriori dettagli, consulta la guida [Best practice ed esempi di policy di accesso](Access-Policy-Best-Practices.md).

## Pagina Impostazioni

La pagina Impostazioni contiene varie opzioni amministrative e di configurazione:

* **Tunnel Cloudflare:** questa sezione elenca tutti i tunnel Cloudflare trovati sul tuo account, il loro stato e gli agenti `cloudflared` connessi. Puoi anche visualizzare tutti i record DNS CNAME che puntano a uno qualsiasi dei tuoi tunnel.
* **Backup e ripristino:** Scarica un archivio di backup DockFlare completo (`.zip`) contenente configurazione crittografata, chiavi dell'agente e stato oppure carica un archivio precedentemente esportato per ripristinare l'istanza.
* **Sicurezza:**
    * **Cambia password:** cambia la password per la Web UI.
    * **Disabilita accesso tramite password:** Per casi d'uso avanzati in cui si posiziona DockFlare dietro un altro proxy di autenticazione. **⚠️ Avvertenza:** Ciò crea un rischio per la sicurezza a causa dell'esposizione alla rete Docker: qualsiasi container sulla stessa rete Docker può ignorare l'autenticazione esterna e accedere direttamente all'API di DockFlare. Consigliamo vivamente di utilizzare invece i provider OAuth/OIDC per comodità di accesso singolo senza sacrificare la sicurezza. Consulta [Accesso alla Web UI](Accessing-the-Web-UI.md) per tutte le implicazioni sulla sicurezza.
* **Credenziali Cloudflare:** ti consente di aggiornare l'ID account Cloudflare e il token API dopo la configurazione iniziale.
* **Configurazione principale:** consente di modificare impostazioni come il nome del tunnel e il periodo di tolleranza della regola.
