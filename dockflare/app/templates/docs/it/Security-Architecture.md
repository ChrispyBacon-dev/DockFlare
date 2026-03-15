# Architettura e hardening della sicurezza di DockFlare

Questo documento spiega come DockFlare protegge sia il nodo Master sia gli agenti registrati in DockFlare 3.0+. Integra l'audit di sicurezza descrivendo le protezioni incluse nel prodotto e le pratiche operative consigliate.

## 1. Modello di fiducia del control plane

- **Il Master come fonte di verità** – DockFlare Master conserva tutte le credenziali Cloudflare e le definizioni delle policy. Gli agenti non gestiscono mai direttamente i token API; eseguono solo istruzioni ricevute tramite un canale autenticato.
- **Chiavi API per agente** – La registrazione richiede una chiave API univoca generata dal Master. Le chiavi vengono archiviate nel registro cifrato `agent_keys.dat` insieme ai metadati di audit (proprietario, timestamp, stato), così da poter essere ruotate o revocate in qualsiasi momento.
- **Protezione delle API del Master** – Gli endpoint amministrativi (interfaccia web, `/api/v2/*`) richiedono una sessione valida o la chiave API del Master. I token vengono oscurati nelle risposte e nei log e possono essere ruotati senza riavviare lo stack.

## 2. Configurazione cifrata e gestione delle chiavi

- **`dockflare_config.dat` cifrato** – Le credenziali Cloudflare, gli account dell'interfaccia web, i valori predefiniti dei tunnel e la chiave master vengono salvati in un blob cifrato protetto da `dockflare.key`.
- **Registro agenti cifrato** – Le chiavi API degli agenti e i relativi metadati di audit risiedono in `agent_keys.dat`, cifrato con la stessa chiave Fernet. I dati sensibili non compaiono più in `state.json`.
- **Riavvio automatico dopo un restore** – Quando viene ripristinato un archivio di backup, DockFlare scrive gli artefatti cifrati, ricarica lo stato di runtime, imposta il flag di riavvio ed esce. La policy di riavvio di Docker fa ripartire subito il container con la nuova configurazione.
- **`state.json` in chiaro per l'osservabilità** – `state.json` resta leggibile in testo semplice, così gli operatori possono controllare regole e agenti. I file cifrati restano la fonte autorevole per i segreti.

## 3. Garanzie di backup e ripristino

- **Contenuto dell'archivio** – Ogni backup (`dockflare_backup_*.zip`) contiene `dockflare_config.dat`, `dockflare.key`, `agent_keys.dat`, `state.json` e `manifest.json` con checksum e metadati di versione. Non servono file aggiuntivi per ricostruire un nodo Master.
- **Flusso di restore automatizzato** – Il ripristino tramite il wizard iniziale o la pagina Settings scrive gli artefatti, ricarica le cache di runtime e forza il riavvio del container, così la configurazione cifrata viene applicata subito.
- **Compatibilità con versioni precedenti** – Il caricamento di un file `state.json` autonomo resta supportato per troubleshooting o migrazioni parziali. DockFlare importa lo stato di runtime ma mantiene la configurazione cifrata esistente, evitando reset accidentali delle credenziali.

## 4. Sicurezza della rete e delle comunicazioni

- **Trasporto tramite tunnel Cloudflare** – Gli agenti non espongono porte in ingresso. Tutto il traffico passa attraverso il tunnel Cloudflare gestito dal Master, riducendo la superficie di attacco sugli host remoti.
- **Chiamate agenti autenticate** – Le chiamate REST degli agenti includono la rispettiva chiave API e sono associate all'ID agente registrato. Chiavi revocate o token non corrispondenti vengono rifiutati.
- **Livello Redis condiviso** – DockFlare usa Redis per cache, streaming dei log e segnalazione tra thread. Lo stack Compose consigliato mantiene Redis su una rete dedicata `dockflare-internal`, così i workload su `cloudflare-net` non possono raggiungerlo direttamente. Se usi un servizio Redis esterno, proteggilo con autenticazione e TLS.
- **Runtime a privilegi minimi** – Sia il Master sia gli agenti vengono eseguiti come utente `dockflare` (UID/GID 65532) e comunicano con Docker solo tramite il socket proxy incluso, mantenendo minima la superficie API esposta.

## 5. Autenticazione e autorizzazione

- **Accesso all'interfaccia web protetto** – Il wizard iniziale impone la creazione di un account amministratore per l'interfaccia web. L'accesso con password può essere disabilitato, ma **lo sconsigliamo fortemente** per le implicazioni di sicurezza sulla rete Docker.
- **Gestione delle sessioni** – Le sessioni Flask-Login sono legate alla configurazione cifrata. Il ripristino di un backup o la rotazione delle credenziali invalida automaticamente le sessioni esistenti.
- **ACL degli agenti** – Ogni record agente tiene traccia dell'assegnazione del tunnel, dei timestamp heartbeat e dei comandi in coda. Il Master invia comandi solo agli agenti che presentano il token corretto e risultano registrati.

### ⚠️ Importante: avviso di sicurezza su "Disable Password Login"

DockFlare include l'impostazione "Disable Password Login" per scenari avanzati in cui DockFlare è già protetto da un livello di autenticazione esterno, ad esempio Cloudflare Access. **Per la maggior parte dei deployment, ne sconsigliamo vivamente l'uso**.

**Rischi di sicurezza quando è abilitata:**
- **Tutti gli endpoint API diventano accessibili senza autenticazione**
- **Esposizione sulla rete Docker:** anche se DockFlare è protetto da Cloudflare Access verso Internet, i container sulla stessa rete Docker possono aggirare l'autenticazione esterna e raggiungere direttamente l'API di DockFlare
- **Nessun controllo di autenticazione a livello applicativo:** l'applicazione presume che la sicurezza venga gestita interamente da un sistema esterno

**Esempio di vettore di attacco:**
```
Internet → Cloudflare Access (Protected) → DockFlare ✅
         ↓
Docker Network → Other Container → DockFlare API (Unprotected) ❌
```

**Approccio consigliato:**
Invece di disabilitare l'autenticazione con password, usa una di queste opzioni sicure:
1. **Credenziali locali DockFlare** – Autenticazione integrata con username e password direttamente in DockFlare
2. **Provider OAuth/OIDC** – Configura Google, GitHub, Azure AD o altri identity provider per avere SSO senza compromettere la sicurezza

Entrambe le opzioni garantiscono un'autenticazione corretta mantenendo la comodità del Single Sign-On. L'opzione OAuth offre l'esperienza SSO senza i rischi derivanti dalla disattivazione dell'autenticazione.

**In sintesi:** salvo architetture molto specifiche e ben isolate a livello di rete, lascia attivo l'accesso con password e usa OAuth per una migliore esperienza d'uso.

## 6. Audit e visibilità operativa

- **Tracciamento dei metadati** – Le chiavi agente registrano `created_at`, `last_used_at`, `bound_agent_id`, stato ed eventi di revoca. `state.json` riflette anche i timestamp dell'ultimo contatto dell'agente per controlli rapidi di integrità.
- **Streaming dei log** – I log in tempo reale passano tramite pub/sub Redis. I valori sensibili (token, chiavi) vengono oscurati prima di arrivare al client.
- **API di stato** – `/api/v2/overview` riunisce lo stato di salute di tunnel, agenti e configurazione per sistemi di monitoraggio o workflow GitOps.

## 7. Raccomandazioni di deployment

| Area | Raccomandazione |
| --- | --- |
| Volumi Docker | Rendi persistente `/app/data` (configurazione cifrata, chiavi, stato). Mantieni anche `/app/logs` se abiliti il file logging e assicurati che i mount host siano scrivibili da UID/GID 65532 o dai build args personalizzati. |
| Redis | Esegui `redis:7-alpine` insieme a DockFlare su una rete privata (`dockflare-internal`) oppure punta `REDIS_URL` a un'istanza già protetta con autenticazione e TLS. Evita di esporre Redis pubblicamente. Usa `REDIS_DB_INDEX` per separare i dati DockFlare da altri container che condividono la stessa istanza Redis. |
| Backup | Scarica regolarmente il file `.zip` e conservalo insieme a `dockflare.key`. Per decifrare la configurazione durante il ripristino servono entrambi. |
| Agenti | Tratta le chiavi API come credenziali sensibili. Distribuisci gli agenti con il socket proxy, così restano esposti solo gli endpoint Docker necessari, e ricorda che il container gira come utente non privilegiato `dockflare` (UID/GID 65532); allinea i permessi host o ricompila con `DOCKFLARE_UID/DOCKFLARE_GID` adeguati. |
| Reverse proxy | Metti DockFlare dietro Cloudflare Access o un altro IdP affidabile. Se disabiliti il login con password, assicurati che l'autenticazione a monte venga sempre applicata. |
| Monitoraggio | Genera avvisi per riavvii inattesi, heartbeat degli agenti mancanti o nuova emissione di chiavi fuori dalle finestre di manutenzione. |

## 8. Miglioramenti futuri (roadmap)

- Protezione opzionale con passphrase per la chiave Fernet a riposo.
- Rotazione automatica delle chiavi agente con periodi di grazia per rollout graduali.
- Scope dei comandi agente più granulari per separare operazioni di sola lettura e di modifica.

---

DockFlare continua a evolvere con un'attenzione costante alla sicurezza. Consulta le note di rilascio per i prossimi miglioramenti di hardening e contribuisci con idee tramite il tracker dei problemi se hai bisogno di controlli aggiuntivi.
