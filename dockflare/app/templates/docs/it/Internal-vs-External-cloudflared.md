# Interno ed esterno `cloudflared`

DockFlare può funzionare in due modalità per gestire l'agente `cloudflared`, che è il pezzo di software che crea effettivamente la connessione persistente tra il tuo server e la rete Cloudflare. Comprendere queste due modalità è fondamentale per scegliere la configurazione giusta per il proprio ambiente.

## Modalità interna (predefinita)

In modalità interna, DockFlare si assume la piena responsabilità della gestione dell'agente `cloudflared`.

### Come funziona
All'avvio di DockFlare, automaticamente:
1. Crea un contenitore Docker dedicato che esegue l'immagine `cloudflare/cloudflared`.
2. Configura questo contenitore dell'agente per connetterti al tuo account Cloudflare e utilizzare il tunnel specificato nelle impostazioni di DockFlare.
3. Assicurarsi che l'agente sia in esecuzione e riavviarlo se fallisce.
4. Applicare automaticamente tutte le impostazioni pertinenti, come l'abilitazione dell'endpoint delle metriche Prometheus.

Questa è la modalità **predefinita e consigliata** per la maggior parte degli utenti.

### Pro
* **Semplicità:** È una configurazione a "configurazione zero". DockFlare gestisce tutto per te.
* **Compatibilità garantita:** DockFlare garantisce che l'agente sia configurato in modo da poter funzionare.
* **Gestione centralizzata:** Tutto ciò che riguarda i tuoi tunnel è gestito da DockFlare.

### Contro
* **Meno controllo:** hai un controllo limitato sulla configurazione dell'agente `cloudflared` oltre ciò che DockFlare espone.

---

## Modalità `cloudflared` esterna

In modalità esterna, sei responsabile dell'esecuzione e della gestione dell'agente `cloudflared` da solo. DockFlare si connetterà a questo agente esistente invece di crearne uno proprio.

### Come funziona
DockFlare **non** creerà un contenitore `cloudflared`. Si presuppone invece che tu abbia un agente `cloudflared` in esecuzione da qualche parte che può utilizzare. Questo potrebbe essere:
* Un processo `cloudflared` in esecuzione direttamente sul sistema operativo host (ad esempio, come servizio `systemd`).
* Un contenitore `cloudflared` che gestisci tu stesso con un file `docker-compose.yml` separato o un comando di esecuzione Docker.
* Un agente `cloudflared` in esecuzione su una macchina completamente diversa.

Si tratta di una **modalità avanzata** destinata agli utenti con esigenze specifiche o configurazioni esistenti complesse.

### Pro
* **Massimo controllo:** hai il controllo completo sull'agente `cloudflared`, inclusa la sua versione, gli argomenti della riga di comando e il ciclo di vita.
* **Integrazione con configurazioni esistenti:** Perfetto se disponi già di un agente `cloudflared` in esecuzione per altri scopi.
* **Disaccoppiamento:** Disaccoppia il ciclo di vita di DockFlare dal ciclo di vita dell'agente `cloudflared`.

### Contro
* **Complessità:** Sei responsabile di garantire che l'agente `cloudflared` sia in esecuzione, configurato correttamente e connesso al tunnel corretto.
* **Caratteristiche di configurazione:** È necessario configurare DockFlare per utilizzare questo agente esterno.

### Come abilitare la modalità esterna
Per abilitare la modalità esterna, è necessario impostare le seguenti variabili di ambiente per il contenitore DockFlare:

* `USE_EXTERNAL_CLOUDFLARED=true`: abilita la modalità esterna.
* `EXTERNAL_TUNNEL_ID`: deve essere impostato sull'UUID del tunnel che l'agente `cloudflared` esterno è configurato per utilizzare.

Quando queste variabili sono impostate, DockFlare salterà la gestione dell'agente interno e invierà invece tutte le configurazioni delle regole ingress al tunnel specificato da `EXTERNAL_TUNNEL_ID`.
