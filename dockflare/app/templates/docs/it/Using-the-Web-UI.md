# Uso dell'interfaccia web

L'interfaccia web di DockFlare è il punto centrale per gestire, monitorare e configurare i tuoi servizi. Consente di svolgere comodamente operazioni che vanno oltre la semplice configurazione delle etichette Docker.

## La dashboard (pagina principale)

La prima pagina che vedi dopo aver effettuato l'accesso è la dashboard principale. Qui puoi controllare rapidamente lo stato di tutti i servizi gestiti.

* **Tabella delle regole ingress gestite:** questa tabella elenca tutte le regole ingress gestite da DockFlare, sia che provengano da un container Docker sia che siano state create manualmente.
    * **Nome host:** il nome host pubblico del servizio.
    * **Servizio:** l'URL di destinazione interno.
    * **Origine:** indica se la regola proviene da `Docker` oppure se è stata creata manualmente dall'interfaccia.
    * **Stato:** mostra se la regola è `active`, `pending_deletion` oppure se ha un `UI Override`.
    * **Accesso:** visualizza il gruppo di accesso applicato e il badge della modalità. Quando vengono sincronizzate le policy riutilizzabili, puoi vedere anche etichette come `Public` o `Authenticated`, i nomi dei gruppi e collegamenti rapidi alla dashboard di Cloudflare.
    * **Gestisci regola:** questo pulsante consente di modificare la regola selezionata.
* **Registri in tempo reale:** sotto la tabella trovi un visualizzatore che mostra in streaming i log del backend DockFlare, molto utile per il debug.

## Gestione delle regole

L'interfaccia web ti offre il pieno controllo sulle regole ingress.

* **Aggiungi regola manuale:** il pulsante "Aggiungi regola manuale" ti consente di creare regole ingress per servizi che non sono in esecuzione in Docker, ad esempio un servizio su un altro computer della tua LAN. Il modulo consente di specificare hostname, URL del servizio e, facoltativamente, un gruppo di accesso.
* **Modifica una regola:** il pulsante "Gestisci regola" accanto a ogni regola apre una finestra modale in cui puoi modificarne la configurazione. Da qui puoi anche applicare un `UI Override` a una regola originariamente creata dalle etichette Docker.
* **Ripristina le etichette:** se una regola Docker ha un `UI Override`, viene visualizzato un pulsante "Ripristina alle etichette", che annulla le modifiche manuali e restituisce il controllo alle etichette Docker.

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

### Policy predefinite della zona (`*.tld`)

La seconda sezione mostra le **Zone Default Policies**, una funzionalità di best practice di sicurezza che protegge tutti i sottodomini:

* **Stato di protezione:** i badge visivi mostrano quali zone DNS hanno una policy wildcard `*.domain.com` (Protetta 🛡️) e quali no (Non protetta ⚠️).
* **Crea policy di zona:** fai clic su "Crea policy" su qualsiasi zona non protetta per creare un'applicazione di accesso con wildcard.
* **Seleziona policy:** scegli quale gruppo di accesso deve proteggere tutti i sottodomini della zona; può trattarsi di bypass pubblico, autenticazione o una policy personalizzata.
* **Rete di protezione:** anche se dimentichi di aggiungere una policy a un servizio specifico, la policy wildcard a livello di zona continuerà a proteggerlo.

**Best practice:** crea policy predefinite di zona per tutti i tuoi domini. Per i domini pubblici, utilizza il criterio di bypass predefinito. Per i domini interni o privati, usa una policy di autenticazione. In questo modo nessun sottodominio verrà esposto accidentalmente.

Per ulteriori dettagli, consulta la guida [Best practice ed esempi di policy di accesso](Access-Policy-Best-Practices.md).

## Pagina Impostazioni

La pagina Impostazioni contiene varie opzioni amministrative e di configurazione:

* **Tunnel Cloudflare:** questa sezione elenca tutti i tunnel Cloudflare trovati sul tuo account, il loro stato e gli agenti `cloudflared` connessi. Puoi anche visualizzare tutti i record DNS CNAME che puntano a uno qualsiasi dei tuoi tunnel.
* **Backup e ripristino:** Scarica un archivio di backup DockFlare completo (`.zip`) contenente configurazione crittografata, chiavi dell'agente e stato oppure carica un archivio precedentemente esportato per ripristinare l'istanza.
* **Sicurezza:**
    * **Cambia password:** cambia la password dell'interfaccia web.
    * **Disabilita accesso tramite password:** opzione pensata per casi d'uso avanzati in cui DockFlare è protetto da un altro proxy di autenticazione. **⚠️ Avvertenza:** questo crea un rischio di sicurezza perché qualsiasi container sulla stessa rete Docker può aggirare l'autenticazione esterna e accedere direttamente all'API di DockFlare. Quando possibile, è preferibile usare provider OAuth/OIDC per ottenere il single sign-on senza compromettere la sicurezza. Consulta [Accesso all'interfaccia web](Accessing-the-Web-UI.md) per tutti i dettagli.
* **Credenziali Cloudflare:** ti consente di aggiornare l'ID account Cloudflare e il token API dopo la configurazione iniziale.
* **Configurazione principale:** consente di modificare impostazioni come il nome del tunnel e il periodo di tolleranza della regola.
