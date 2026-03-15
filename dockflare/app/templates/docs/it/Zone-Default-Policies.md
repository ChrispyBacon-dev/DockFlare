# Politiche predefinite della zona: protezione con wildcard

## Panoramica

Le policy predefinite di zona sono una funzionalità di sicurezza che utilizza le applicazioni wildcard di Cloudflare Access (`*.domain.com`) per proteggere automaticamente tutti i sottodomini di una zona DNS.

## Il problema che questo risolve

Senza policy predefinite della zona:
- I servizi dimenticati vengono pubblicamente esposti
- I nuovi sottodomini non hanno protezione finché non vengono configurati manualmente
- Gli errori di battitura nelle configurazioni del nome host ignorano i controlli di accesso
- La deriva della documentazione comporta lacune in termini di sicurezza

## Come funziona

### Priorità politica

Cloudflare valuta le policy di accesso in questo ordine:

1. **Corrispondenza esatta del nome host** (ad esempio, `app.example.com`)
2. **Corrispondenza con wildcard** (ad esempio, `*.example.com`)
3. **Nessuna corrispondenza** = Accesso pubblico (nessuna app Access)

### Implementazione DockFlare

La sezione **Zone Default Policies** di DockFlare:
- Elenca tutte le tue zone DNS Cloudflare
- Mostra lo stato della protezione con badge visivi
- Consente la creazione con un clic delle norme `*.zone.com`
- Permette di scegliere quale Gruppo di Accesso protegge la zona

## Guida all'installazione

### Passaggio 1: rivedi le tue zone

1. Passare alla pagina **Criteri di accesso**
2. Scorrere fino a **Criteri predefiniti della zona (wildcard *.tld)**
3. Esaminare lo stato della protezione:
   - 🛡️ **Verde "Protetto"** - La zona ha una policy wildcard
   - ⚠️ **Giallo "Non protetto"** - La zona è vulnerabile

### Passaggio 2: creare policy di zona

Per ogni zona non protetta:

1. Fai clic sul pulsante **Crea policy**
2. La finestra modale mostra il nome host `*.zone-name.com`
3. Selezionare la politica di accesso appropriata:
   - **Zone pubbliche** → `public-default-bypass`
   - **Zone interne** → Politica di autenticazione
   - **Zone miste** → Politica più restrittiva
4. Fai clic su **Crea policy di zona**

### Passaggio 3: verifica in Cloudflare

1. Apri il dashboard di Cloudflare Zero Trust
2. Passare a Accesso → Applicazioni
3. Cerca le applicazioni denominate `Zone Default: *.domain.com`
4. Verificare che la politica sia corretta

## Raccomandazioni sulla sicurezza

### Ambienti di produzione

✅ **Abilita sempre i criteri predefiniti di zona**
- Previene l'esposizione accidentale
- Rileva gli errori di configurazione
- Protegge dagli attacchi di rilevamento dei sottodomini

### Strategia di selezione delle politiche

- **Domini di contenuti pubblici** (blog, marketing): `public-default-bypass`
- **Domini strumenti interni**: autenticazione e-mail/dominio
- **Domini di dati sensibili**: autenticazione abilitata per MFA
- **Domini di sviluppo**: bloccali con la politica più rigorosa

### Monitoraggio

Revisionare regolarmente:
- Quali zone hanno protezione (pagina **Politiche di accesso**)
- Accedi ai log dell'applicazione in Cloudflare
- Elenco dei sottodomini attivi rispetto alle policy configurate

## Risoluzione dei problemi

### Errore "La policy esiste già"

Esiste già un'applicazione di accesso `*.domain.com`. Questo potrebbe essere:
- Creato manualmente in Cloudflare
- Creato da DockFlare in precedenza
- Creato da un altro strumento

**Soluzione:** Gestiscilo direttamente in Cloudflare oppure elimina e ricrea tramite DockFlare.

### Servizio ancora accessibile senza autenticazione

Controlla la priorità della politica:
1. Verificare che il servizio abbia una politica del nome host specifica
2. Verifica che la wildcard della zona esista e sia configurata correttamente
3. Se il servizio deve restare pubblico nonostante la protezione della zona, aggiungi l'etichetta `dockflare.access.group=public-default-bypass`

### Aggirare la protezione delle zone per i servizi pubblici

Se disponi di una policy di autenticazione a livello di zona ma hai bisogno che servizi specifici rimangano pubblici:

1. Aggiungere l'etichetta bypass al contenitore:
   ```yaml
   labels:
     - "dockflare.access.group=public-default-bypass"
   ```
2. In questo modo viene creata un'applicazione di accesso per il nome host esatto con decisione di bypass
3. Le policy specifiche del nome host sovrascrivono le policy wildcard
4. Il servizio diventa accessibile al pubblico mentre la zona rimane protetta
5. Controlla i log di accesso di Cloudflare per verificare l'ordine di valutazione delle policy
6. Assicurati che il record DNS punti al tunnel corretto

### Zona non visualizzata nell'elenco

Possibili cause:
- Zona DNS non nel tuo account Cloudflare
- Il token API non dispone dell'autorizzazione `Zone:Zone:Read`
- La zona è in pausa o eliminata

**Soluzione:** verificare che la zona esista nella dashboard di Cloudflare e che il token API disponga delle autorizzazioni corrette.

## Migliori pratiche

1. **Crea prima le policy di zona** - Prima di aggiungere servizi
2. **Utilizza l'autenticazione per le zone interne** - Non utilizzare mai il bypass
3. **Documenta le eccezioni** - Se una zona non necessita di protezione, documentane il motivo
4. **Controlli regolari** - Revisione mensile dello stato di protezione della zona
5. **Test prima della produzione**: verifica che la policy wildcard non interrompa i servizi esistenti
6. **Principio del privilegio minimo**: utilizza la politica più restrittiva che consente comunque l'accesso legittimo

## Configurazioni di esempio

### Zona blog pubblica
```
Zone: blog.example.com
Policy: public-default-bypass
Result: All subdomains publicly accessible (*.blog.example.com)
```

### Zona Strumenti Interni
```
Zone: internal.company.com
Policy: Company Email Authentication
Result: All subdomains require @company.com email (*.internal.company.com)
```

### Zona di sviluppo misto
```
Zone: dev.company.com
Policy: Developer Team Authentication
Result: All dev services protected by default (*.dev.company.com)
Specific overrides: public-demo.dev.company.com → public-default-bypass
```

## Comprendere le priorità politiche

### Scenario 1: la policy specifica sovrascrive il carattere jolly

**Configurazione:**
- Politica di zona: `*.example.com` → Richiede l'autenticazione
- Politica specifica: `blog.example.com` → `public-default-bypass`

**Risultato:**
- `blog.example.com` → Pubblico (prevale la policy specifica)
- `api.example.com` → Richiede l'autenticazione (la policy wildcard lo protegge)
- `forgotten.example.com` → Richiede l'autenticazione (la policy wildcard lo protegge)

### Scenario 2: wildcard come rete di sicurezza

**Configurazione:**
- Politica di zona: `*.internal.company.com` → Richiede l'e-mail @company.com
- Politica specifica: nessuna per `test-server.internal.company.com`

**Risultato:**
- `test-server.internal.company.com` → Richiede l'autenticazione (la policy wildcard lo protegge)
- Anche se ti sei dimenticato di configurarlo, la policy di zona lo protegge

### Scenario 3: nessuna protezione

**Configurazione:**
- Politica di zona: nessuna per `*.risky-domain.com`
- Politica specifica: `app.risky-domain.com` → Autenticazione

**Risultato:**
- `app.risky-domain.com` → Richiede autenticazione (politica specifica)
- `forgotten.risky-domain.com` → ⚠️ **PUBLIC** (nessuna policy wildcard a proteggerlo)

## Integrazione con le etichette DockFlare

### Utilizzo dell'etichetta `default_tld`

L'etichetta `dockflare.access.policy=default_tld` indica a DockFlare di utilizzare la policy wildcard della zona:

```yaml
services:
  my-service:
    image: nginx
    labels:
      - "dockflare.enable=true"
      - "dockflare.hostname=new-app.internal.company.com"
      - "dockflare.service=http://my-service:80"
      - "dockflare.access.policy=default_tld"
```

**Comportamento:**
- Se `*.internal.company.com` esiste → Eredita quella policy
- Se non esiste alcuna policy di zona → Il servizio è pubblico (nessuna app di accesso creata)

### Raccomandazione

Invece di fare affidamento sull'etichetta `default_tld`:
1. Crea policy predefinite della zona nell'interfaccia web
2. Lascia che la policy wildcard protegga automaticamente tutti i servizi
3. Crea solo policy specifiche per le eccezioni

Ciò garantisce una migliore sicurezza per impostazione predefinita.

## Documentazione correlata

- [Best practice per le politiche di accesso](Access-Policy-Best-Practices.md)
- [Uso dell'interfaccia web](Using-the-Web-UI.md)
- [Etichette contenitori](Container-Labels.md)
- [Come funziona DockFlare](How-DockFlare-Works.md)
- [Architettura di sicurezza](Security-Architecture.md)
