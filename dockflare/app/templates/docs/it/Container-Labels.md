# Riferimento per le etichette dei contenitori

DockFlare è configurato principalmente tramite etichette Docker allegate ai tuoi contenitori. Questa pagina fornisce un riferimento completo per tutte le etichette supportate.

## Configurazione di base

Queste etichette controllano il routing fondamentale e la definizione del servizio per un contenitore.

| Etichetta | Descrizione | Esempio |
| :--- | :--- | :--- |
| `dockflare.enable` | **Obbligatorio.** L'interruttore principale. Deve essere impostato su `true` affinché DockFlare possa gestire il contenitore. | `dockflare.enable=true` |
| `dockflare.hostname` | **Obbligatorio.** Il nome host pubblico del tuo servizio. | `dockflare.hostname=myservice.example.com` |
| `dockflare.service` | **Obbligatorio.** L'URL interno del servizio a cui Cloudflare Tunnel deve connettersi. Può essere `http`, `https`, `tcp`, `ssh`, `rdp`, `http_status:XXX` o `bastion`. | `dockflare.service=http://my-app-container:8080` |
| `dockflare.path` | Il percorso URL da instradare a questo servizio. Utile per esporre più servizi sullo stesso nome host. | `dockflare.path=/api` |
| `dockflare.zonename` | (Facoltativo) Zona Cloudflare esplicita (dominio) in cui deve essere creato il record DNS. Se omesso, DockFlare ora rileva automaticamente la zona in base al nome host e torna al valore predefinito configurato (`CF_ZONE_ID`) solo quando il rilevamento automatico fallisce. | `dockflare.zonename=another-domain.com` |
| `dockflare.no_tls_verify` | Se impostato su `true`, disabilita la verifica del certificato TLS per la connessione tra `cloudflared` e il tuo servizio di origine. Utile per origini con certificati autofirmati. | `dockflare.no_tls_verify=true` |
| `dockflare.originsrvname` | Imposta un nome host SNI (Server Name Indication) specifico per la connessione TLS all'origine. Questo è noto anche come "Nome server di origine" nella dashboard di Cloudflare. | `dockflare.originsrvname=internal.service.local` |
| `dockflare.httpHostHeader` | Sostituisce l'intestazione `Host` inviata da `cloudflared` al tuo servizio di origine. | `dockflare.httpHostHeader=custom-host.internal` |
| `dockflare.http2_origin` | Se impostato su `true`, abilita il protocollo HTTP/2 per la connessione tra `cloudflared` e il tuo servizio di origine. Obbligatorio per i servizi gRPC. Si applica solo ai servizi HTTP/HTTPS. | `dockflare.http2_origin=true` |
| `dockflare.disable_chunked_encoding` | Se impostato su `true`, disabilita la codifica del trasferimento in blocchi su HTTP/1.1. Utile per server WSGI (Flask, Django, FastAPI) e altre origini che non supportano correttamente le richieste in blocchi. Si applica solo ai servizi HTTP/HTTPS. | `dockflare.disable_chunked_encoding=true` |

> **Suggerimento:** a partire da DockFlare v3.0, puoi saltare `dockflare.zonename` per la maggior parte dei carichi di lavoro. Il Master rileva la zona Cloudflare corretta facendo corrispondere il suffisso del nome host e torna alla zona predefinita configurata solo quando non riesce a trovare una corrispondenza. Fornisci l'etichetta quando desideri inserire intenzionalmente un record in una zona diversa.

> **Nota:** l'opzione **Abbina SNI all'host** di Cloudflare è disponibile nella configurazione manuale delle regole DockFlare nel dashboard. Attualmente non è impostato tramite un'etichetta Docker.

---

## Configurazione della politica di accesso

Queste etichette ti consentono di creare e gestire dinamicamente le applicazioni Cloudflare Access per proteggere i tuoi servizi.

**Nota:** si consiglia vivamente di utilizzare **Gruppi di accesso** (`dockflare.access.group`) per la gestione delle policy. DockFlare 3.0.3 sincronizza ogni gruppo di accesso con una policy di accesso Cloudflare riutilizzabile denominata, offrendoti un riutilizzo uno-a-molti e modifiche bidirezionali. L'utilizzo di etichette individuali è la soluzione migliore per configurazioni uniche e una tantum. Se viene utilizzato `dockflare.access.group` o `dockflare.access.groups`, tutte le altre etichette `dockflare.access.*` verranno ignorate.

### Cambiamenti importanti nella v3.0.3

#### Criterio di bypass predefinito del sistema

A partire dalla versione 3.0.3, quando utilizzi `dockflare.access.policy=bypass` o `dockflare.access.group=bypass`, il tuo servizio farà riferimento alla policy riutilizzabile `public-default-bypass` gestita dal sistema invece di creare una policy in linea. Ciò mantiene pulita la dashboard di Cloudflare.

- **Prima della versione 3.0.3:** ciascuna regola di bypass creava una policy in linea separata
- **v3.0.3+:** Tutte le regole di bypass condividono una policy canonica `public-default-bypass`

#### Migrazione delle etichette legacy

DockFlare migra automaticamente le etichette di bypass legacy per utilizzare la policy di sistema centralizzata:

- `dockflare.access.policy=bypass` → Utilizza il criterio di sistema `public-default-bypass`
- `dockflare.access.group=bypass` → Utilizza il criterio di sistema `public-default-bypass`

La migrazione avviene in modo trasparente durante l'elaborazione e la riconciliazione del contenitore. I tuoi contenitori continueranno a funzionare senza che siano necessarie modifiche.

#### Configurazione dell'accesso semplificato

Per scenari di accesso complessi (autenticazione di posta elettronica/dominio, whitelist IP, ecc.), ora è consigliabile:

1. Crea un gruppo di accesso nella pagina **Criteri di accesso**
2. Fai riferimento con `dockflare.access.group=your-group-id`

Le opzioni di creazione rapida sono state rimosse dall'interfaccia web per incoraggiare questo flusso di lavoro basato sulle best practice.

#### Etichetta policy predefinita della zona

L'etichetta `dockflare.access.policy=default_tld` funziona ancora ed erediterà la protezione dalla politica dei wildcard `*.domain.com` della tua zona. Se non esiste alcuna policy di zona, il servizio sarà pubblico (nessuna app di accesso).

**Raccomandazione:** crea policy predefinite di zona per tutti i tuoi domini nell'interfaccia utente per una maggiore sicurezza.

| Etichetta | Descrizione | Esempio |
| :--- | :--- | :--- |
| `dockflare.access.group` | L'ID di un singolo gruppo di accesso preconfigurato da applicare a questo servizio. L'ID può essere trovato nella pagina "Policy di accesso" nell'interfaccia web di DockFlare. | `dockflare.access.group=internal-tools-policy` |
| `dockflare.access.groups` | Un elenco separato da virgole di ID gruppo di accesso da applicare. Ciò consente di sovrapporre più policy su un unico servizio. | `dockflare.access.groups=allow-team-a,allow-admins` |
| `dockflare.access.policy` | Il tipo di policy principale. Può essere `bypass` (pubblico), `authenticate` (richiede l'accesso) o `default_tld` (eredita da una policy `*.domain.com`). Se non impostato, il servizio sarà pubblico. Preferire i gruppi di accesso per policy riutilizzabili; queste etichette sono per sostituzioni specializzate. | `dockflare.access.policy=authenticate` |
| `dockflare.access.name` | Un nome personalizzato per l'applicazione Cloudflare Access. Il valore predefinito è `DockFlare-{hostname}`. | `dockflare.access.name=My Web App Access` |
| `dockflare.access.session_duration` | La durata della sessione per gli utenti autenticati (ad esempio, `24h`, `30m`). Il valore predefinito è `24h`. | `dockflare.access.session_duration=1h` |
| `dockflare.access.app_launcher_visible` | Se `true`, rende l'applicazione visibile nell'App Launcher di Cloudflare Access. | `dockflare.access.app_launcher_visible=true` |
| `dockflare.access.allowed_idps` | Un elenco separato da virgole degli UUID consentiti del provider di identità (IdP). Puoi trovarli nella dashboard di Cloudflare Zero Trust. | `dockflare.access.allowed_idps=uuid1,uuid2` |
| `dockflare.access.auto_redirect_to_identity` | Se `true`, gli utenti verranno immediatamente reindirizzati alla pagina di accesso dell'IdP anziché alla pagina iniziale di accesso a Cloudflare. | `dockflare.access.auto_redirect_to_identity=true` |
| `dockflare.access.custom_rules` | Una stringa JSON che rappresenta una serie di regole della policy di accesso Cloudflare. Ciò fornisce la massima flessibilità per politiche complesse e una tantum. | `dockflare.access.custom_rules='[{"email":{"email":"user@example.com"},"action":"allow"}]'` |

---

## Etichette indicizzate per più domini

DockFlare supporta la definizione di più nomi host per un singolo contenitore utilizzando etichette indicizzate. Ciò è utile per esporre porte o percorsi diversi dello stesso servizio su nomi host pubblici diversi.

Per utilizzare le etichette indicizzate, anteporre all'etichetta un numero intero, a partire da `0`.

* È sempre richiesto un nome host indicizzato (`<index>.hostname`).
* Altre etichette nello stesso indice (ad esempio, `<index>.service`, `<index>.path`) sovrascriveranno le etichette di base (non indicizzate) per quello specifico nome host.
* Se non viene fornita un'etichetta indicizzata, tornerà al valore dell'etichetta di base corrispondente.

### Esempio

Questo esempio espone due nomi host da un singolo container:
1. `app.example.com` instrada all'interfaccia web principale sulla porta `80`.
2. `api.example.com` instrada verso l'API sulla porta `3000` ed è protetto con uno specifico gruppo di accesso.

```yaml
services:
  my-multi-service:
    image: my-app
    labels:
      - "dockflare.enable=true"

      # --- Definition 0 ---
      - "dockflare.0.hostname=app.example.com"
      - "dockflare.0.service=http://my-multi-service:80"

      # --- Definition 1 ---
      - "dockflare.1.hostname=api.example.com"
      - "dockflare.1.service=http://my-multi-service:3000"
      - "dockflare.1.access.group=api-access-policy"
```
