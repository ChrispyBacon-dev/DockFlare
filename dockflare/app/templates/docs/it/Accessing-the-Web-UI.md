# Accesso all'interfaccia web

Una volta avviato correttamente il container DockFlare, puoi accedere all'interfaccia web per gestire le impostazioni, controllare lo stato dei tunnel e configurare manualmente le regole ingress.

## URL predefinito

Per impostazione predefinita, l'interfaccia web di DockFlare è disponibile sulla porta `5000`. Per accedervi, apri il browser e vai a questo URL:

```
http://<your-server-ip>:5000
```

Sostituisci `<your-server-ip>` con l'indirizzo IP del server su cui è in esecuzione DockFlare.

## Configurazione iniziale

La prima volta che accedi all'interfaccia web, verrai guidato dall'**assistente di configurazione iniziale**. L'assistente ti aiuta a:

1. Ripristinare un archivio di backup DockFlare esistente (`dockflare_backup_*.zip`). Se scegli questa opzione, il sistema importa la configurazione cifrata, lo stato e le chiavi degli agenti, quindi riavvia automaticamente il container per applicarli.
2. Creare un account amministratore e una password per l'interfaccia web.
3. Inserire l'ID account Cloudflare, l'ID zona (facoltativo) e il token API.
4. Confermare le impostazioni del tunnel e completare i passaggi iniziali.

## Accesso

Dopo la configurazione iniziale, ogni volta che apri l'interfaccia web ti verrà mostrata la schermata di login. Usa la password creata durante la configurazione per accedere.

## Disabilitare l'accesso con password

DockFlare include l'impostazione "Disabilita accesso con password", pensata per distribuzioni avanzate in cui DockFlare è già protetto da un livello di autenticazione esterno, come Cloudflare Access. **Per la maggior parte dei casi, ne sconsigliamo fortemente l'uso.**

### Perché esiste questa impostazione

Se esegui DockFlare dietro Cloudflare Access o un altro proxy di autenticazione che impone l'SSO prima dell'accesso all'applicazione, puoi disabilitare il login integrato con password per evitare una doppia autenticazione.

### Rischi di sicurezza quando è abilitata

- ⚠️ **Tutti gli endpoint API diventano accessibili senza autenticazione** quando questa impostazione è abilitata
- ⚠️ **Esposizione sulla rete Docker:** anche se DockFlare è protetto da Cloudflare Access su Internet pubblico, i container sulla stessa rete Docker possono aggirare l'autenticazione esterna e accedere direttamente all'API di DockFlare
- ⚠️ **Nessuna applicazione interna dell'autenticazione:** l'applicazione presume che la sicurezza sia gestita interamente dal livello di autenticazione esterno

### Esempio di vettore di attacco

```
Internet → Cloudflare Access (Protected) → DockFlare ✅
         ↓
Docker Network → Other Container → DockFlare API (Unprotected) ❌
```

Anche quando DockFlare è protetto da Cloudflare Access verso Internet, qualsiasi container in esecuzione sulla stessa rete Docker può aggirare questa protezione e accedere direttamente agli endpoint API di DockFlare senza autenticazione.

### Approccio consigliato

Invece di disabilitare l'autenticazione con password, usa una di queste opzioni sicure:

1. **Credenziali locali di DockFlare** - Autenticazione semplice con password integrata in DockFlare
2. **Provider OAuth/OIDC** - Configura Google, GitHub, Azure AD o altri provider di identità per un single sign-on pratico senza rinunciare alla sicurezza (vedi [Configurazione provider OAuth](OAuth-Provider-Setup.md))

Entrambe le opzioni garantiscono un'autenticazione corretta mantenendo la comodità dell'SSO. L'opzione OAuth offre l'esperienza di single sign-on senza i rischi legati alla disattivazione dell'autenticazione.

### In sintesi

A meno che tu non abbia un'architettura di sicurezza molto specifica e ben compresa, con isolamento di rete adeguato, lascia abilitato il login con password e usa OAuth per maggiore comodità.
