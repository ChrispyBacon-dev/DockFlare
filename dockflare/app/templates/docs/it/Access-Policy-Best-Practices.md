# Best practice ed esempi di policy di accesso

La funzionalità di sicurezza più potente di DockFlare sono i **Gruppi di accesso**. Forniscono un modo centralizzato, riutilizzabile e gestibile per proteggere i tuoi servizi utilizzando Cloudflare Zero Trust.

## La "regola d'oro": utilizzare i gruppi di accesso

La best practice più importante è **utilizzare i gruppi di accesso per tutte le policy di accesso comuni**.

I gruppi di accesso sono modelli di policy creati nell'interfaccia web di DockFlare. Invece di definire regole complesse con più etichette su ogni container, crei una policy una sola volta e la applichi con un'unica etichetta chiara. DockFlare v3.0.3 sincronizza ogni gruppo con una policy di accesso Cloudflare riutilizzabile, così lo stesso insieme di decisioni può essere applicato a più applicazioni.

---

## Come creare e utilizzare i gruppi di accesso

La creazione di un gruppo di accesso è un processo semplice che si svolge interamente nell'interfaccia web di DockFlare.

### Passaggio 1: crea il gruppo di accesso

1. Vai alla pagina **Policy di accesso** dalla barra di navigazione principale nell'interfaccia web di DockFlare.
2. Fai clic sul pulsante **"Aggiungi gruppo di accesso"**.
3. Assegna al tuo gruppo un **ID univoco e descrittivo**. Questo ID è quello che utilizzerai nelle etichette Docker. Ad esempio: `admin-users`, `home-network`, `geo-block`.
4. Seleziona la **Modalità di accesso** dalle schede nella parte superiore della finestra modale:
    * **Autenticato** richiede agli utenti di accedere ed emette una decisione `allow`.
    * **Pubblico** utilizza una decisione `bypass` in modo che l'applicazione rimanga aperta pur rispettando i filtri geografici.
5. Compila gli input visualizzati per la modalità selezionata (e-mail per Autenticato, elenco paesi opzionale per entrambi).
6. Regola le impostazioni opzionali come la durata della sessione, la visibilità dell'App Launcher e il reindirizzamento IdP automatico se sei in modalità autenticata.
7. Salva il gruppo. DockFlare scrive la definizione localmente e la sincronizza su Cloudflare come `DockFlare-AccessGroup-<id>`.

### Passaggio 2: applicare il gruppo di accesso

Una volta creato, hai due modi per applicare il tuo gruppo di accesso a un servizio:

#### A) Con un'etichetta Docker (il modo consigliato)

Per qualsiasi container nuovo o esistente, aggiungi semplicemente l'etichetta `dockflare.access.group` con l'ID del gruppo che hai creato.

```yaml
services:
  grafana:
    image: grafana/grafana
    labels:
      - "dockflare.enable=true"
      - "dockflare.hostname=monitoring.example.com"
      - "dockflare.service=http://grafana:3000"
      # Apply the entire policy with one simple label:
      - "dockflare.access.group=admin-users"
```
Puoi anche applicare più gruppi utilizzando `dockflare.access.groups` con un elenco di ID separati da virgole:
`dockflare.access.groups=admin-users,home-network`

#### Politiche gestite dal sistema

DockFlare fornisce due policy di sistema integrate che sono automaticamente disponibili:

- **`public-default-bypass`** - Accesso pubblico con decisione di bypass (utilizzo per servizi realmente pubblici)
- **`authenticated-default`** - Autenticazione predefinita con PIN una tantum + limitazione e-mail

Queste policy di sistema non sono eliminabili e fungono da base per la protezione della zona e la migrazione delle etichette legacy.

#### B) Dall'interfaccia web (per regole manuali o sostituzioni)

Puoi anche applicare un gruppo di accesso a qualsiasi regola direttamente dalla dashboard:
1. Trova la regola ingress che desideri modificare nella dashboard principale.
2. Fai clic sul pulsante **"Gestisci regola"**.
3. Nella modalità di modifica, seleziona i gruppi di accesso desiderati dal menu a discesa "Gruppi di accesso".
4. Salva le modifiche.

Ciò è perfetto per applicare policy a regole create manualmente (per servizi non Docker) o per sovrascrivere temporaneamente una policy definita dalle etichette Docker.

---

## Esempi di politiche

Di seguito sono riportate alcune configurazioni di policy comuni che puoi creare all'interno di un gruppo di accesso.

### Esempio 1: autenticazione tramite e-mail

Questo è il caso d'uso più comune: consentire solo a utenti specifici che possono autenticarsi con il provider di identità configurato (ad esempio Google, GitHub o un PIN monouso inviato alla loro email).

* **ID gruppo:** `admin-users`
* **Modalità:** *Autenticata*
* **E-mail consentite:** `user1@example.com`, `user2@example.com`
* **Durata della sessione:** `24h`

DockFlare crea una policy riutilizzabile con una decisione `allow` per le email elencate e una regola `deny` fall-through per tutti gli altri. Applica il gruppo con `dockflare.access.group=admin-users`.

### Esempio 2: consenti il tuo indirizzo IP di casa

Questa policy limita l'accesso alla tua rete domestica, consentendoti di saltare la richiesta di accesso quando ti trovi su un IP attendibile e di imporre l'autenticazione altrove.

1. **Trova il tuo IP pubblico:** nel browser, cerca "qual è il mio IP". Verrà visualizzato il tuo indirizzo IP pubblico (ad esempio, `203.0.113.55`).
2. **Crea il gruppo di accesso:**
    * **ID gruppo:** `home-network`
    * **Modalità:** *Autenticata*
    * **E-mail consentite:** `you@example.com`
    * **Ignora IP:** aggiungi `203.0.113.55/32` al campo della lista consentita degli IP

DockFlare genera una policy che prima ignora il tuo intervallo IP e quindi richiede l'autenticazione delle e-mail elencate. Tutti gli altri ricevono una decisione di rifiuto.

### Esempio 3: Geo-fencing (blocco di più paesi)

Questa politica mantiene pubblico il tuo sito di marketing limitando il traffico proveniente da regioni specifiche.

* **ID gruppo:** `public-eu`
* **Modalità:** *Pubblico*
* **Paesi bloccati:** `RU`, `CN`, `KP`

La policy riutilizzabile risultante emette una decisione Cloudflare `bypass` per tutti, esclusi i paesi elencati. Combinalo con altri gruppi se hai bisogno di sovrapporre controlli aggiuntivi (`dockflare.access.groups=public-eu,admin-users`).

---

## Policy predefinite della zona: best practice per la sicurezza

### Cosa sono le policy predefinite della zona?

Le policy predefinite della zona sono applicazioni di accesso wildcard `*.domain.com` che proteggono TUTTI i sottodomini di una zona DNS, inclusi quelli che non hai ancora configurato esplicitamente.

### Perché ne hai bisogno

**Il problema:** se dimentichi di aggiungere una policy di accesso a un servizio, questa viene esposta pubblicamente per impostazione predefinita.

**La soluzione:** una policy con wildcard a livello di zona funge da rete di sicurezza. Anche se dimentichi di configurare `forgotten-service.yourdomain.com`, la policy `*.yourdomain.com` lo rileverà.

### Come configurarli

1. Passare alla pagina **Criteri di accesso**
2. Scorrere fino alla sezione **Politiche predefinite della zona (wildcard *.tld)**
3. Cerca le zone con il badge "Non protetto" ⚠️
4. Fai clic su **Crea policy**
5. Selezionare il gruppo di accesso appropriato:
   - **Per domini pubblici:** utilizza `public-default-bypass`
   - **Per domini interni:** utilizzare una policy di autenticazione
   - **Per uso misto:** utilizza la policy più restrittiva

### Migliori pratiche

- ✅ **Crea sempre policy di zona** per i domini di produzione
- ✅ **Utilizza criteri di autenticazione** per zone interne/private
- ✅ **Utilizzare la tangenziale pubblica** solo per le zone veramente pubbliche
- ✅ **Rivedi regolarmente** - controlla mensilmente lo stato di protezione della zona
- ⚠️ **Ricorda la priorità** - Le policy specifiche del nome host sovrascrivono le policy wildcard

### Ordine di priorità politica

Cloudflare valuta le policy di accesso in questo ordine:

1. **Corrispondenza esatta del nome host** (ad esempio, `app.example.com`) - Priorità più alta
2. **Corrispondenza con wildcard** (ad esempio, `*.example.com`) - Fallback
3. **Nessuna corrispondenza** = Accesso pubblico (nessuna app di accesso) - Impostazione predefinita

Ciò significa che puoi avere una policy predefinita di zona restrittiva e creare comunque eccezioni specifiche per i singoli servizi.

---

## Gestione delle policy Cloudflare esterne

### Comprendere i tipi di policy

DockFlare visualizza tre tipi di policy nella pagina Politiche di accesso, ciascuna con un badge visivo:

- **🟦 DockFlare** - Politiche create e gestite da DockFlare (prefisso: `DockFlare-`)
- **🟪 Esterno** - Politiche create all'esterno di DockFlare (manuale o altri strumenti)
- **🟧 Sistema** - Criteri di sistema non eliminabili (`public-default-bypass`, `authenticated-default`)

### Sincronizzazione dei criteri esterni

Per impostazione predefinita, DockFlare importa solo le policy con il prefisso `DockFlare-`. Ciò mantiene l'elenco delle policy pulito e focalizzato sull'infrastruttura dei contenitori.

**Per sincronizzare TUTTE le policy Cloudflare** (incluse quelle create manualmente):

1. Imposta la variabile d'ambiente: `SYNC_ALL_CLOUDFLARE_POLICIES=true`
2. Riavvia DockFlare
3. Fare clic su **"Sincronizza da Cloudflare"** nella pagina Politiche di accesso

Le norme esterne verranno visualizzate con un badge viola **"Esterno"**.

### Perché importare policy esterne?

**Pro:**
- Visibilità completa dell'intera configurazione di accesso a Cloudflare
- Riutilizzare le policy esistenti senza ricrearle
- Gestione centralizzata in un'unica interfaccia
- Applicare qualsiasi politica a qualsiasi servizio (gestito da DockFlare o meno)

**Contro:**
- Elenco di policy più lungo se disponi di numerose policy esterne
- Rischio di modificare accidentalmente le politiche utilizzate dai servizi non DockFlare

### Organizzare le tue politiche

**Suggerimento avanzato:** rinomina le policy esterne in Cloudflare per utilizzare il prefisso `DockFlare-`

Puoi organizzare le policy esterne rinominandole nella dashboard di Cloudflare:

1. Apri la policy in **Cloudflare Zero Trust**
2. Rinominarlo per utilizzare il prefisso `DockFlare-` (ad esempio, `DockFlare-LegacyVPN` o `DockFlare-ThirdPartyApp`)
3. Fare clic su **"Sincronizza da Cloudflare"** in DockFlare
4. La policy ora appare come una policy **gestita da DockFlare** (badge blu)

Ciò ti consente di:
- ✅ Raggruppa tutte le policy visibili da DockFlare con nomi coerenti
- ✅ Filtra e ordina le polizze per tipologia
- ✅ Distinguere "gestito da DockFlare" da "appena visibile in DockFlare"

### Politiche di filtraggio

Utilizza il menu a discesa **Filtro** per visualizzare tipi di policy specifici:

- **Tutte le politiche** - Mostra tutto (DockFlare, Esterno, Sistema)
- **DockFlare-Managed** - Mostra solo le policy con badge blu
- **Esterno** - Mostra solo le polizze con badge viola
- **Sistema**: mostra solo i criteri di sistema

### Caratteristiche di sicurezza

**Protezione tramite policy esterna:**

Quando si eliminano o si modificano policy esterne, DockFlare visualizza un avviso:

> ⚠️ ATTENZIONE: questa è una policy ESTERNA non creata da DockFlare.
>
> La modifica di questa politica potrebbe influire sui servizi esterni a DockFlare.
>
> Sei assolutamente sicuro?

Ciò impedisce modifiche accidentali alle policy gestite da altri strumenti o configurazioni manuali.

### Migliori pratiche

1. **Configurazione predefinita (consigliata):**
   - Mantieni `SYNC_ALL_CLOUDFLARE_POLICIES=false` (predefinito)
   - Vengono visualizzate solo le policy gestite da DockFlare
   - Elenco delle politiche pulito e mirato

2. **Configurazione avanzata (utenti esperti):**
   - Abilita `SYNC_ALL_CLOUDFLARE_POLICIES=true`
   - Visualizza e gestisci TUTTE le politiche in un unico posto
   - Rinominare le policy esterne nel prefisso `DockFlare-` per l'organizzazione

3. **Approccio ibrido:**
   - Mantieni la sincronizzazione disabilitata per impostazione predefinita
   - Rinominare manualmente importanti policy esterne in `DockFlare-*` in Cloudflare
   - Appariranno automaticamente dopo la successiva sincronizzazione

4. **Convenzione di denominazione delle policy:**
   ```
   DockFlare-AccessGroup-<id>     # Auto-generated by access groups
   DockFlare-<custom-name>         # Your renamed external policies
   <anything-else>                 # Pure external (only visible if sync enabled)
   ```
