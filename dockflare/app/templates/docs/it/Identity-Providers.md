# Provider di identità

> **📌 Importante:** questa guida serve per configurare i **provider di identità per le policy di accesso Cloudflare** al fine di proteggere servizi e applicazioni. Se invece vuoi configurare OAuth/OIDC per **l'accesso all'interfaccia web di DockFlare**, consulta [Configurazione provider OAuth](OAuth-Provider-Setup.md).

I provider di identità (IdP) abilitano l'autenticazione OAuth/OIDC per le applicazioni protette da Cloudflare Zero Trust. DockFlare semplifica la gestione degli IdP e la loro integrazione nelle policy di accesso.

## Panoramica

Invece di affidarti solo all'autenticazione basata sulle email, puoi usare provider OAuth diffusi come Google, GitHub, Azure AD e altri. Gli utenti si autenticano con i loro account esistenti, ottenendo un'esperienza di accesso fluida e sicura.

## Provider supportati

DockFlare supporta i seguenti provider di identità:

- **Google** - Account Google personali
- **Google Workspace** - Account Google Workspace (G Suite) con restrizione di dominio facoltativa
- **Microsoft Azure AD** - Microsoft Entra ID (Azure Active Directory)
- **Okta** - Okta Identity Cloud
- **GitHub** - GitHub OAuth
- **OpenID Connect generico** - Qualsiasi provider conforme a OIDC

## Gestione dei provider di identità

### Aggiungere un provider di identità

1. Vai alla pagina **Policy di accesso**.
2. Nella sezione **Provider di identità**, fai clic su **Aggiungi provider**.
3. Compila i campi richiesti:
   - **Nome descrittivo**: nome interno usato da DockFlare, ad esempio `google-main` o `github-dev`
   - **Nome visualizzato**: nome mostrato nella dashboard Cloudflare
   - **Tipo di provider**: seleziona il provider OAuth
   - **Configurazione**: credenziali specifiche del provider, come descritto nelle guide sotto
4. Fai clic su **Crea provider**.
5. Prova il provider usando l'URL di test fornito.

### Sincronizzare da Cloudflare

Se hai già configurato IdP in Cloudflare Zero Trust:

1. Fai clic su **Sincronizza da Cloudflare** nella sezione Provider di identità.
2. DockFlare importerà tutti gli IdP esistenti e genererà automaticamente nomi descrittivi.
3. Potrai rinominare questi nomi per renderli più facili da usare nelle etichette.

### Testare un provider di identità

Dopo aver creato un IdP, puoi testarlo:

1. Fai clic sul menu **⋮** accanto al provider.
2. Seleziona **Prova IdP**.
3. Si aprirà una nuova finestra in cui potrai autenticarti.
4. Verifica che il flusso di accesso funzioni correttamente.

## Guide alla configurazione del provider

### Google (account personali)

**Passaggio 1: crea le credenziali OAuth**

1. Vai a [Google Cloud Console](https://console.cloud.google.com/).
2. Crea un nuovo progetto o selezionane uno esistente.
3. Vai a **API e servizi** → **Credenziali**.
4. Fai clic su **Crea credenziali** → **ID client OAuth**.
5. Seleziona **Applicazione web**.
6. Aggiungi l'URI di reindirizzamento autorizzato:
   ```
   https://<your-team>.cloudflareaccess.com/cdn-cgi/access/callback
   ```
   <small>Puoi trovare il nome del tuo team in <a href="https://one.dash.cloudflare.com/{{ACCOUNT_ID}}/settings/custom_pages" target="_blank">Zero Trust</a>, in Impostazioni > Pagine personalizzate.</small>
7. Copia **ID client** e **segreto client**.

**Passaggio 2: configura in DockFlare**

- **ID client**: incolla il valore da Google Cloud Console
- **Segreto client**: incolla il valore da Google Cloud Console

---

### Google Workspace

Uguale alla configurazione Google sopra, con un campo facoltativo aggiuntivo:

- **Apps Domain**: (facoltativo) limita l'accesso a un dominio specifico, ad esempio `example.com`

Se specificato, potranno autenticarsi solo gli utenti con indirizzi email `@example.com`.

---

### Microsoft Azure AD

**Passaggio 1: registra l'applicazione in Azure**

1. Vai al [Portale di Azure](https://portal.azure.com/).
2. Vai a **Azure Active Directory** → **Registrazioni app**.
3. Fai clic su **Nuova registrazione**.
4. Assegna un nome all'applicazione, ad esempio `DockFlare Access`.
5. In **URI di reindirizzamento**, seleziona **Web** e inserisci:
   ```
   https://<your-team>.cloudflareaccess.com/cdn-cgi/access/callback
   ```
   <small>Puoi trovare il nome del tuo team in <a href="https://one.dash.cloudflare.com/{{ACCOUNT_ID}}/settings/custom_pages" target="_blank">Zero Trust</a>, in Impostazioni > Pagine personalizzate.</small>
6. Fai clic su **Registra**.
7. Copia **ID applicazione (client)**.
8. Copia **ID directory (tenant)**.
9. Vai a **Certificati e segreti** → **Nuovo segreto client**.
10. Crea un segreto e copia il **valore**.

**Passaggio 2: configura in DockFlare**

- **ID applicazione (client)**: incolla il valore da Azure
- **ID directory (tenant)**: incolla il valore da Azure
- **Segreto client**: incolla il valore da Azure

---

### GitHub

**Passaggio 1: crea l'app OAuth**

1. Vai a [Impostazioni sviluppatore GitHub](https://github.com/settings/developers).
2. Fai clic su **Nuova app OAuth**.
3. Compila i dettagli:
   - **Nome dell'applicazione**: DockFlare Access
   - **URL della home page**: `https://your-domain.com`
   - **URL di callback dell'autorizzazione**:
     ```
     https://<your-team>.cloudflareaccess.com/cdn-cgi/access/callback
     ```
     <small>Puoi trovare il nome del tuo team in <a href="https://one.dash.cloudflare.com/{{ACCOUNT_ID}}/settings/custom_pages" target="_blank">Zero Trust</a>, in Impostazioni > Pagine personalizzate.</small>
4. Fai clic su **Registra applicazione**.
5. Copia **ID client**.
6. Fai clic su **Genera un nuovo segreto client** e copialo.

**Passaggio 2: configura in DockFlare**

- **ID client**: incolla il valore da GitHub
- **Segreto client**: incolla il valore da GitHub

---

### Okta

**Passaggio 1: crea l'applicazione in Okta**

1. Accedi alla tua [console di amministrazione Okta](https://admin.okta.com/).
2. Vai a **Applicazioni** → **Crea integrazione app**.
3. Seleziona **OIDC - OpenID Connect**.
4. Scegli **Applicazione web**.
5. Configura:
   - **URI di reindirizzamento per il login**:
     ```
     https://<your-team>.cloudflareaccess.com/cdn-cgi/access/callback
     ```
     <small>Puoi trovare il nome del tuo team in <a href="https://one.dash.cloudflare.com/{{ACCOUNT_ID}}/settings/custom_pages" target="_blank">Zero Trust</a>, in Impostazioni > Pagine personalizzate.</small>
6. Fai clic su **Salva**.
7. Copia **ID client** e **segreto client**.
8. Annota il tuo **dominio Okta**, ad esempio `https://dev-12345.okta.com`.

**Passaggio 2: configura in DockFlare**

- **URL account Okta**: il tuo dominio Okta, ad esempio `https://dev-12345.okta.com`
- **ID client**: incolla il valore da Okta
- **Segreto client**: incolla il valore da Okta

---

### OpenID Connect generico

Per qualsiasi provider conforme a OIDC:

**Passaggio 1: ottieni la configurazione del provider**

Dalla documentazione del tuo IdP, recupera:
- URL di autorizzazione
- URL del token
- URL JWKS (JSON Web Key Set)
- ID client
- Segreto client

**Passaggio 2: configura in DockFlare**

- **URL di autorizzazione**: endpoint OAuth di autorizzazione del provider
- **URL del token**: endpoint del token del provider
- **URL JWKS**: endpoint JWKS del provider, usato per la verifica della firma
- **ID client**: valore fornito dal provider
- **Segreto client**: valore fornito dal provider

---

## Uso dei provider di identità nelle policy di accesso

### Nei gruppi di accesso

1. Vai a **Policy di accesso** → **Policy di accesso avanzate**.
2. Fai clic su **Crea nuovo gruppo** oppure modifica un gruppo esistente.
3. Nella sezione **Regole della policy**:
   - **Provider di identità**: seleziona uno o più IdP
   - **Email o domini consentiti**: **obbligatorio quando usi IdP**. Specifica gli indirizzi email autorizzati.
4. Salva il gruppo.

### Modalità di autenticazione

Hai due opzioni:

1. **Solo email**: inserisci gli indirizzi email e non selezionare alcun IdP. Gli utenti si autenticano con un PIN monouso.
2. **IdP + email (obbligatorio)**: seleziona uno o più IdP e inserisci le email consentite. Gli utenti devono autenticarsi tramite l'IdP selezionato ed essere presenti nell'elenco delle email autorizzate.

**⚠️ Avviso di sicurezza:** quando utilizzi provider di identità, **devi** specificare gli indirizzi email consentiti. Questo evita accessi non autorizzati. Per esempio, senza restrizioni sulle email, scegliere `Google` come IdP permetterebbe a chiunque abbia un account Google di accedere al servizio.

### Nelle etichette Docker

Usa il nome descrittivo nelle etichette dei container:

```yaml
services:
  myapp:
    image: myapp:latest
    labels:
      dockflare.enable: "true"
      dockflare.hostname: "app.example.com"
      dockflare.access.group: "my-access-group"
```

Il gruppo di accesso `my-access-group` risolverà automaticamente i nomi descrittivi degli IdP negli UUID Cloudflare.

---

## Best practice

### Convenzioni di denominazione

Usa nomi descrittivi e chiari:
- ✅ `google-main`, `github-dev`, `azure-work`
- ❌ `idp1`, `test`, `new`

### Sicurezza

- **Ruota regolarmente i segreti**: aggiorna periodicamente i segreti client
- **Limita l'ambito**: per Google Workspace e Azure AD, restringi l'accesso a domini specifici quando possibile
- **Testa prima della produzione**: prova sempre gli IdP prima di applicarli ai servizi di produzione
- **Monitora l'utilizzo**: controlla i log di Cloudflare per individuare tentativi di accesso non autorizzati

### Ambienti multipli

Crea IdP separati per ambienti differenti:
- `google-dev` - Ambiente di sviluppo
- `google-staging` - Ambiente di staging
- `google-prod` - Ambiente di produzione

### Requisiti email con gli IdP

**IMPORTANTE:** per motivi di sicurezza, l'autenticazione IdP richiede sempre restrizioni sulle email.

**Esempio di gruppo di accesso:**
- **Provider di identità**: `google-main`
- **Email consentite**: `admin@example.com, user@example.com, @contractor-domain.com`

Questa configurazione consente l'accesso agli utenti che:
- Si autenticano tramite l'IdP `google-main` (Google OAuth) **E**
- Hanno un indirizzo email corrispondente a `admin@example.com`, `user@example.com` o a qualsiasi email `@contractor-domain.com`

**Come funziona:**
1. L'utente fa clic su Accedi nell'applicazione protetta.
2. Viene reindirizzato al login Google OAuth.
3. Dopo l'autenticazione Google, Cloudflare verifica che l'email sia nell'elenco consentito.
4. L'accesso viene concesso solo se l'email corrisponde all'elenco autorizzato.

---

## Risoluzione dei problemi

### Errore "URI di reindirizzamento non valido"

**Causa**: l'URI di reindirizzamento configurato nel provider OAuth non corrisponde a quello previsto da Cloudflare.

**Soluzione**: assicurati di aver aggiunto esattamente questo URI:
```
https://<your-team>.cloudflareaccess.com/cdn-cgi/access/callback
```
<small>Puoi trovare il nome del tuo team in <a href="https://one.dash.cloudflare.com/{{ACCOUNT_ID}}/settings/custom_pages" target="_blank">Zero Trust</a>, in Impostazioni > Pagine personalizzate.</small>

Sostituisci `<your-team>` con il nome del tuo team Cloudflare Zero Trust.

---

### "Test IdP non riuscito"

**Causa**: credenziali errate o configurazione non corretta.

**Soluzione**:
1. Verifica che ID client e segreto client siano corretti.
2. Controlla che l'applicazione OAuth sia abilitata presso il provider.
3. Per Azure AD, verifica sia l'ID client sia l'ID tenant.
4. Prova il provider usando l'URL di test di Cloudflare.

---

### "Impossibile eliminare l'IdP gestito dal sistema"

**Causa**: stai tentando di eliminare il provider integrato One-Time PIN.

**Soluzione**: il provider `onetimepin` è gestito dal sistema e non può essere eliminato. È necessario per l'autenticazione OTP basata su email.

---

### "IdP non trovato nell'etichetta Docker"

**Causa**: stai usando l'UUID Cloudflare invece del nome descrittivo nell'etichetta.

**Soluzione**: usa il nome descrittivo, ad esempio `google-main`, al posto dell'UUID nella configurazione del gruppo di accesso.

---

## Documentazione correlata

- [Best practice per le policy di accesso](Access-Policy-Best-Practices.md)
- [Policy predefinite di zona](Zone-Default-Policies.md)
- [Etichette dei container](Container-Labels.md)
- [Architettura di sicurezza](Security-Architecture.md)

---
