# Controlli sanitari

DockFlare include un endpoint di controllo dello stato dedicato che può essere utilizzato con il meccanismo di controllo dello stato integrato di Docker. Ciò consente a Docker di monitorare lo stato dell'applicazione DockFlare e di riavviarla automaticamente se non risponde.

## L'endpoint `/ping`

DockFlare espone un semplice endpoint HTTP su `/ping`.

* **Scopo:** Fornire ai sistemi automatizzati un modo semplice per verificare se il server web DockFlare è in esecuzione e reattivo.
* **Autenticazione:** questo endpoint è **esente da autenticazione**. Non è necessario effettuare l'accesso per accedervi, il che è ciò che consente al meccanismo di controllo dello stato interno di Docker di utilizzarlo.
* **Risposta sana:** Un'applicazione DockFlare sana e in esecuzione risponderà a una richiesta su `/ping` con un codice di stato **HTTP 200 OK**.
* **Informazioni sulla versione:** Il corpo della risposta dall'endpoint `/ping` contiene anche la versione in esecuzione dell'applicazione DockFlare.

## Come configurare un controllo dello stato in Docker Compose

Puoi aggiungere una sezione `healthcheck` al servizio `dockflare` nel tuo file `docker-compose.yml` per fare in modo che Docker monitori automaticamente lo stato dell'applicazione.

```yaml
services:
  dockflare:
    image: alplat/dockflare:stable
    container_name: dockflare
    restart: unless-stopped
    # ... other settings
    healthcheck:
      # The command to run to check health.
      # curl is used to make an HTTP request to the ping endpoint.
      test: ["CMD", "curl", "-f", "http://localhost:5000/ping"]
      # How often to run the check
      interval: 1m30s
      # How long to wait for a response
      timeout: 10s
      # How many consecutive failures before marking as unhealthy
      retries: 3
      # How long to wait after the container starts before running the first check
      start_period: 40s
```

### Suddivisione della configurazione `healthcheck`:

* `test`: questo è il comando che Docker esegue all'interno del contenitore. `curl -f` effettuerà una richiesta HTTP all'endpoint `/ping` e uscirà con un codice di stato diverso da zero se la risposta non è HTTP 200 OK.
* `interval`: Docker eseguirà questo controllo ogni 90 secondi.
* `timeout`: Docker attenderà fino a 10 secondi per il completamento del comando.
* `retries`: se il controllo fallisce 3 volte di seguito, Docker contrassegnerà il contenitore come `unhealthy`.
* `start_period`: Docker attenderà 40 secondi dopo l'avvio del contenitore prima di eseguire il primo controllo dello stato. Ciò dà all'applicazione il tempo di inizializzarsi correttamente.

Con questa configurazione in atto, puoi verificare lo stato del tuo contenitore eseguendo `docker ps`. La colonna di stato mostrerà `(healthy)` se il controllo di integrità ha superato. Se il contenitore diventa non integro, Docker lo riavvierà automaticamente in base alla policy `restart` (ad esempio, `unless-stopped`).