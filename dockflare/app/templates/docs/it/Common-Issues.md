# Problemi comuni

Questa pagina elenca alcuni dei problemi comuni che gli utenti potrebbero riscontrare e come risolverli.

---

### Problema: il contenitore DockFlare non si avvia o è in un ciclo di riavvio.

**Soluzione:**
1. **Controlla i log di Docker:** Il primo passo è sempre controllare i log del contenitore DockFlare. Esegui il seguente comando:
    ```bash
    docker logs dockflare
    ```
2. **Cerca errori:** cerca eventuali messaggi di errore. Le cause comuni includono:
    * Un file `docker-compose.yml` non valido (ad esempio, sintassi errata, problemi di montaggio del volume).
    * Problemi con il demone Docker stesso.
    * Problemi di connettività o autorizzazione con il servizio docker-socket-proxy o l'impostazione `DOCKER_HOST`.

---

### Problema: i record DNS non vengono creati in Cloudflare.

**Soluzione:**
1. **Controlla i registri DockFlare:** Cerca eventuali messaggi di errore relativi all'API Cloudflare. I log spesso ti diranno esattamente perché la chiamata API non è riuscita.
2. **Verifica le autorizzazioni del token API:** questa è la causa più comune. Assicurati che il tuo token API Cloudflare disponga delle autorizzazioni richieste. Come minimo, hai bisogno di:
    * `Zone:DNS:Edit` per ogni zona che desideri che DockFlare gestisca.
    * `Zone:Zone:Read`
3. **Verifica la configurazione della zona:**
    * Assicurati che l'**ID zona** fornito durante la configurazione sia corretto.
    * Se utilizzi l'etichetta `dockflare.zonename`, verifica che il nome della zona sia scritto correttamente.

---

### Problema: una policy di accesso (Zero Trust) non viene applicata a un servizio.

**Soluzione:**
1. **Controlla le autorizzazioni del token API:** assicurati che il tuo token API disponga dell'autorizzazione `Account:Access: Apps and Policies:Edit`.
2. **Verifica le sostituzioni dell'interfaccia utente:** Nella dashboard DockFlare, controlla se la regola ha lo stato "Sostituzione dell'interfaccia utente". Le sostituzioni dell'interfaccia utente hanno la precedenza sulle etichette.
3. **Verifica l'ID del gruppo di accesso:** Se stai utilizzando `dockflare.access.group`, assicurati che l'ID specificato nell'etichetta **esattamente** corrisponda all'ID creato per il gruppo di accesso nella pagina "Criteri di accesso".
4. **Controlla la dashboard di Cloudflare:** accedi alla dashboard di Cloudflare Zero Trust. Passare a **Accesso -> Applicazioni** per verificare se l'applicazione di accesso è stata creata. A volte, Cloudflare mostrerà un errore che non è visibile nella risposta API.

---

### Problema: ricevo un errore `ERR_TOO_MANY_REDIRECTS` quando provo ad accedere al mio servizio.

**Soluzione:**
Questo errore si verifica quasi sempre a causa di un'errata configurazione delle impostazioni SSL/TLS tra il tuo servizio di origine e Cloudflare.

1. **Verifica la modalità SSL/TLS di Cloudflare:** Nella dashboard di Cloudflare, vai alle impostazioni SSL/TLS per il tuo dominio. Assicurati che la modalità di crittografia sia impostata su **Completa (Ristretta)**.
2. **Evita doppi reindirizzamenti:** la modalità SSL "flessibile" in Cloudflare può causare questo problema se anche la tua applicazione backend tenta di reindirizzare da HTTP a HTTPS. Il browser rimane bloccato in un loop.
3. **Utilizza `https` nell'URL del tuo servizio:** se il tuo servizio backend supporta HTTPS, utilizza `https://` nell'etichetta `dockflare.service` (ad esempio, `dockflare.service=https://my-app:443`). Ciò garantisce che anche la connessione da `cloudflared` al tuo servizio sia crittografata.

---

### Problema: un servizio dietro Traefik/Proxmox funziona solo quando è abilitato "Abbina SNI all'host" di Cloudflare.

**Soluzione:**
1. Modifica la regola manuale in DockFlare e abilita **Abbina SNI all'host**.
2. Salva la regola e verifica il percorso in Cloudflare Zero Trust.
3. Se hai bisogno che DockFlare mantenga anche i campi di instradamento lato Cloudflare che DockFlare non modella, vai su **Impostazioni → Impostazioni generali** e abilita **Preserva campi di ingresso Cloudflare non gestiti**.

---

### Problema: il contenitore gestito `cloudflared-agent` non si avvia con un errore di "rete obsoleta".

**Soluzione:**
Ciò può verificarsi se la rete Docker utilizzata dall'agente è stata rimossa e ricreata. DockFlare è progettato per gestirlo automaticamente.

1. **Riavvia DockFlare:** un semplice riavvio del contenitore DockFlare (`docker compose restart dockflare`) dovrebbe risolvere il problema.
2. **Come funziona:** All'avvio, DockFlare controlla lo stato del suo agente gestito. Se rileva questo problema specifico, rimuoverà automaticamente il contenitore dell'agente danneggiato e ne creerà uno nuovo con la configurazione corretta. Si trattava di un bug specifico corretto nella versione `v1.9.5`. Assicurati di utilizzare una versione recente di DockFlare.