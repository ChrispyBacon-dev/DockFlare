# Debug e registri

Quando risolvi i problemi con DockFlare, i tuoi strumenti principali sono i log generati dal contenitore DockFlare e dal suo agente `cloudflared` gestito.

## 1. Controllo dei registri del contenitore DockFlare

La fonte di informazioni più importante è l'output del registro dal contenitore DockFlare stesso. Questi registri forniscono una visione dettagliata e in tempo reale di ciò che sta facendo DockFlare.

### Cosa troverai nei log:
* Rilevamento degli eventi di avvio/arresto del contenitore Docker.
* Elaborazione delle etichette `dockflare.*`.
* Chiamate effettuate all'API Cloudflare.
* Messaggi di successo o risposte di errore dettagliate dall'API Cloudflare.
* Lo stato delle attività in background come la pulizia delle risorse.

### Come visualizzare i registri:
Per visualizzare i log, utilizza il seguente comando Docker nel tuo terminale:
```bash
# View the full log history
docker logs dockflare

# Follow the logs in real-time
docker logs -f dockflare
```

## 2. Utilizzo dei registri in tempo reale dell'interfaccia web

Per comodità, la dashboard DockFlare include un **visualizzatore di log in tempo reale** nella parte inferiore della pagina principale.

Questo visualizzatore trasmette in streaming esattamente gli stessi log che vedresti con `docker logs -f dockflare`, ma fornisce un modo semplice per vedere cosa sta succedendo in questo momento senza uscire dal browser. Ciò è particolarmente utile per osservare le azioni intraprese da DockFlare immediatamente dopo l'avvio o l'arresto di un contenitore.

## 3. Controllo dei registri dell'agente `cloudflared`

Se sospetti che il problema riguardi la connessione tra il tuo server e la rete Cloudflare, puoi controllare direttamente i log del contenitore dell'agente `cloudflared`.

### Come visualizzare i registri dell'agente:
Innanzitutto, devi trovare il nome del contenitore dell'agente. Per impostazione predefinita, si chiama `cloudflared-agent-<tunnel-name>`, dove `<tunnel-name>` è il nome del tunnel configurato nelle impostazioni di DockFlare.

Puoi trovare il nome esatto con `docker ps`.

Una volta che hai il nome, esegui:
```bash
# Replace with the actual container name
docker logs cloudflared-agent-dockflare-tunnel
```

Questi registri sono utili per la diagnosi:
* Errori di connessione al perimetro Cloudflare.
* Problemi di autenticazione con il token del tunnel.
* Errori a livello di protocollo per il traffico proxy.

**Nota:** Ciò si applica solo se si utilizza la **Modalità interna** predefinita. Se utilizzi la [Modalità esterna](External-cloudflared-Mode.md), dovrai controllare i log del tuo processo agente `cloudflared`.

## 4. Controllo della dashboard di Cloudflare

Infine, non dimenticare di utilizzare la dashboard di Cloudflare come strumento di debug.
* **Pagina DNS:** Controlla se i record CNAME sono stati creati come previsto.
* **Dashboard Zero Trust:** Vai su **Accesso -> Tunnel** per verificare lo stato del tuo tunnel e le sue regole ingress.
* **Dashboard Zero Trust:** Vai su **Accesso -> Applicazioni** per verificare la configurazione e l'integrità delle tue policy Zero Trust. Lo stato "Ultimo accesso" sulle polizze può essere molto informativo.
