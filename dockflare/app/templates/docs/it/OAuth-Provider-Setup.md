## Configurazione del provider OAuth

> **📌 Importante:** questa guida serve per configurare l'**autenticazione dell'interfaccia web di DockFlare**. Se invece vuoi configurare OAuth/OIDC per le **policy di accesso Cloudflare** in modo da proteggere i tuoi servizi, consulta [Provider di identità](Identity-Providers.md).

DockFlare consente di delegare l'autenticazione degli utenti a provider esterni tramite lo standard OpenID Connect (OIDC). In questo modo puoi abilitare il single sign-on (SSO) per l'interfaccia web di DockFlare e integrarti con provider di identità come Google, Authentik, Okta e altri.

### Aggiungere un nuovo provider

Segui questi passaggi per aggiungere un nuovo provider OIDC:

1. **Vai alle impostazioni:** dalla dashboard principale apri la pagina **Impostazioni**.
2. **Individua la sezione OAuth:** scorri fino alla sezione **Autenticazione OAuth**.
3. **Aggiungi provider:** fai clic su **Aggiungi provider** per aprire il modulo di configurazione.

Ti verranno mostrati i seguenti campi:

* **Tipo provider:** è impostato su `OpenID Connect (OIDC)`, lo standard moderno per l'autenticazione federata.
* **URL dell'emittente:** è il campo più importante. Rappresenta l'URL di base del provider OIDC, che DockFlare usa per rilevare automaticamente la configurazione del provider. Per esempio: `https://accounts.google.com` oppure `https://authentik.yourdomain.com/application/o/dockflare/`.
* **ID provider:** un nome breve, univoco e in minuscolo per il provider, ad esempio `google` o `authentik-corp`. Questo ID viene utilizzato internamente e nell'URL di callback.
* **Nome visualizzato:** il nome che comparirà sul pulsante di accesso, ad esempio `Google` oppure `Corporate SSO`.
* **ID client:** l'identificatore pubblico dell'applicazione DockFlare, fornito dalla console sviluppatore del provider OIDC.
* **Segreto client:** il segreto riservato dell'applicazione DockFlare, anch'esso ottenuto dalla console del provider OIDC.
* **Abilita provider:** questa casella permette di attivare o disattivare il provider in qualsiasi momento.

Dopo aver compilato i campi, fai clic su **Aggiungi provider** per salvare la configurazione.

### Trovare l'URL di callback

Dopo aver aggiunto un provider, l'**URL di callback** richiesto, noto anche come “Authorized redirect URI”, verrà mostrato sotto la voce del provider nella pagina delle impostazioni.

Devi copiare esattamente questo URL e aggiungerlo all'elenco degli URL di callback consentiti nella console di amministrazione del provider.

---

### Esempio: configurare Google

Ecco una guida rapida per configurare Google come provider OAuth.

1. **Apri Google Cloud Console:** vai alla pagina [API e servizi > Credenziali](https://console.cloud.google.com/apis/credentials).
2. **Crea le credenziali:** fai clic su **+ CREA CREDENZIALI** e seleziona **ID client OAuth**.
3. **Configura l'applicazione:**
   * Imposta **Tipo di applicazione** su **Applicazione Web**.
   * Assegna un nome, per esempio `DockFlare`.
4. **Aggiungi l'URI di reindirizzamento:**
   * In **URI di reindirizzamento autorizzati**, fai clic su **+ AGGIUNGI URI**.
   * Inserisci l'URL di callback fornito da DockFlare. Avrà un aspetto simile a `https://your-dockflare-domain.com/auth/google/callback`.
5. **Crea e copia:** fai clic su **CREA**. Si aprirà una finestra con **ID client** e **Segreto client**. Copia entrambi i valori.
6. **Configura DockFlare:**
   * **URL dell'emittente:** `https://accounts.google.com`
   * **ID provider:** `google`
   * **Nome visualizzato:** `Google`
   * **ID client:** `(Your Client ID from Google)`
   * **Segreto client:** `(Your Client Secret from Google)`

Salva il provider in DockFlare e potrai accedere con il tuo account Google.

---

### Configurare DockFlare con OAuth e policy di accesso

Quando utilizzi l'autenticazione OAuth, potresti voler proteggere l'interfaccia principale di DockFlare con policy di accesso, assicurandoti allo stesso tempo che i callback OAuth continuino a funzionare correttamente. Questo è particolarmente importante se la tua istanza DockFlare è protetta anche da restrizioni IP o da altri controlli di accesso.

#### **Best practice: policy di bypass per i callback OAuth**

Usa etichette indicizzate per creare regole separate per l'interfaccia principale e per i percorsi di callback OAuth:

```yaml
services:
  dockflare:
    image: alplat/dockflare:stable
    labels:
      # Main DockFlare interface with access policy
      - "dockflare.enable=true"
      - "dockflare.hostname=dockflare.example.com"
      - "dockflare.service=http://dockflare:5000"
      - "dockflare.access.group=team"  # your custom access policy

      # OAuth callback paths with bypass policy (required for OAuth to work)
      - "dockflare.0.hostname=dockflare.example.com"
      - "dockflare.0.path=/auth/google/callback"
      - "dockflare.0.service=http://dockflare:5000"
      - "dockflare.0.access.policy=bypass"

      # Add additional callback paths for other providers if needed
      - "dockflare.1.hostname=dockflare.example.com"
      - "dockflare.1.path=/auth/github/callback"
      - "dockflare.1.service=http://dockflare:5000"
      - "dockflare.1.access.policy=bypass"
```

#### **Perché questa configurazione è necessaria**

- **Protezione dell'interfaccia principale:** la dashboard di DockFlare resta protetta dalla policy di accesso scelta
- **Funzionamento di OAuth:** i callback OAuth possono raggiungere DockFlare senza essere bloccati dall'autenticazione
- **Sicurezza:** viene bypassato solo lo specifico percorso di callback, non l'intera applicazione
- **Flessibilità:** funziona con qualsiasi combinazione di policy di accesso, ad esempio basate su IP o su autenticazione

#### **Note importanti**

1. **Corrispondenza esatta del percorso:** il percorso di callback deve corrispondere esattamente a quello previsto dal provider OAuth.
2. **Provider multipli:** aggiungi una regola indicizzata distinta per ogni provider OAuth configurato.
3. **Nessun carattere jolly:** evita i percorsi wildcard per motivi di sicurezza; usa callback URL espliciti.
4. **Test:** dopo la configurazione, verifica sia l'accesso protetto all'interfaccia principale sia il corretto funzionamento del login OAuth.
