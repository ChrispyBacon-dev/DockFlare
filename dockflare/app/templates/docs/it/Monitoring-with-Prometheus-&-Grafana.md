# Monitoraggio con Prometheus & Grafana

L'agente `cloudflared` gestito da DockFlare può esporre un'ampia gamma di parametri di prestazioni e salute nel formato Prometheus. Raccogliendo e visualizzando questi parametri, puoi ottenere informazioni preziose sul traffico, sulla latenza e sui tassi di errore del tuo tunnel.

Questa guida spiega come abilitare l'endpoint delle metriche e fornisce una configurazione rapida per uno stack di monitoraggio utilizzando Prometheus e Grafana.

## Passaggio 1: attiva l'endpoint Metrics in DockFlare

Il primo passaggio è indicare a DockFlare di abilitare l'endpoint delle metriche Prometheus sul suo agente `cloudflared` gestito.

Puoi farlo impostando la variabile di ambiente `CLOUDFLARED_METRICS_PORT` per il tuo contenitore DockFlare.

**Esempio `docker-compose.yml`:**
```yaml
services:
  dockflare:
    image: alplat/dockflare:stable
    # ... other settings
    environment:
      # Enable the metrics endpoint on port 2000 inside the container
      - CLOUDFLARED_METRICS_PORT=2000
```
Quando riavvii DockFlare con questa variabile, ricreerà automaticamente il suo agente `cloudflared` gestito con il server dei parametri abilitato sulla porta specificata.

**Nota:** questa funzione è disponibile solo nella **Modalità interna** predefinita. Se utilizzi la [Modalità esterna](External-cloudflared-Mode.md), sei responsabile dell'abilitazione dell'endpoint delle metriche sul tuo agente `cloudflared`.

## Passaggio 2: imposta uno stack di monitoraggio

Se non disponi già di uno stack di monitoraggio, puoi configurarne rapidamente uno utilizzando Docker Compose. Il repository DockFlare fornisce un esempio di configurazione nella directory `/examples`.

Per una guida completa copia-incolla su come impostare Prometheus e Grafana per monitorare DockFlare, fare riferimento al file **[`grafana quick setup.md`](https://github.com/ChrispyBacon-dev/DockFlare/blob/main/examples/grafana%20quick%20setup.md)** nel repository.

Questa guida ti guiderà attraverso:
1. Creazione della struttura di directory necessaria.
2. Aggiunta dei servizi Prometheus e Grafana al tuo `docker-compose.yml`.
3. Configurazione di Prometheus per ricavare parametri dall'agente `cloudflared`.
4. Fornitura automatica di Grafana con l'origine dati Prometheus.

## Passaggio 3: importa la dashboard Grafana predefinita

Per semplificare la visualizzazione, DockFlare fornisce una dashboard Grafana predefinita progettata per funzionare perfettamente con le metriche esposte dall'agente `cloudflared`.

1. Il dashboard è disponibile come **[`dashboard.json`](https://github.com/ChrispyBacon-dev/DockFlare/blob/main/examples/dashboard.json)** nella directory `/examples` del repository.
2. Scarica questo file.
3. Accedi alla tua istanza di Grafana.
4. Vai alla sezione "Dashboard" e fai clic su "Importa".
5. Carica il file `dashboard.json`.
6. Seleziona la tua origine dati Prometheus e importa la dashboard.

Ora avrai una panoramica completa delle prestazioni del tuo tunnel Cloudflare, inclusi conteggi di richieste, tassi di errore, latenza di connessione e altro ancora.

![Esempio dashboard Grafana](../static/images/grafana_dashboard_example.png)