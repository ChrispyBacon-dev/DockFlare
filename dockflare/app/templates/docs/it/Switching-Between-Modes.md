# Passaggio da una modalità all'altra

Puoi cambiare DockFlare tra le modalità **Interna** (predefinita) e **Esterna** `cloudflared` in qualsiasi momento. Questa guida spiega il processo per una transizione graduale.

Per un confronto dettagliato tra le due modalità, consulta la pagina [Interna ed esterna `cloudflared`](Internal-vs-External-cloudflared.md).

---

## Passaggio dalla modalità interna a quella esterna

Questo processo prevede la configurazione del tuo agente `cloudflared` e quindi la comunicazione a DockFlare di utilizzarlo.

**Passaggio 1: configura l'agente `cloudflared` esterno**

Innanzitutto, devi configurare ed eseguire il tuo agente `cloudflared`. Potrebbe trattarsi di un processo sul sistema operativo host o su un altro contenitore Docker.

* Assicurati che sia configurato per utilizzare uno specifico tunnel Cloudflare.
* Prendi nota del **Tunnel ID** (UUID).
* Avvia l'agente e conferma che funziona correttamente e viene visualizzato come "connesso" nella dashboard di Cloudflare.

**Passaggio 2: riconfigurare e riavviare DockFlare**

Successivamente, devi aggiornare le variabili di ambiente per il tuo contenitore DockFlare per dirgli di passare alla modalità esterna.

Nel tuo `docker-compose.yml`:
```yaml
services:
  dockflare:
    image: alplat/dockflare:stable
    # ... other settings
    environment:
      # Enable external mode
      - USE_EXTERNAL_CLOUDFLARED=true
      # Provide the ID of your running tunnel
      - EXTERNAL_TUNNEL_ID=your-tunnel-uuid-goes-here
```

**Passaggio 3: implementa la modifica**

Esegui `docker compose up -d` per ricreare il contenitore DockFlare con le nuove variabili di ambiente.

Quando viene avviato il contenitore DockFlare aggiornato:
1. Rileverà che `USE_EXTERNAL_CLOUDFLARED` è `true`.
2. **Arresterà e rimuoverà** il proprio contenitore `cloudflared-agent` gestito.
3. Inizierà a inviare tutte le configurazioni delle regole ingress al tunnel specificato da `EXTERNAL_TUNNEL_ID`.

I tuoi servizi verranno ora forniti dal tuo agente `cloudflared` gestito esternamente.

---

## Passaggio dalla modalità esterna a quella interna

Questo processo è più semplice in quanto implica lasciare che DockFlare riprenda il controllo.

**Passaggio 1: riconfigurare DockFlare**

Rimuovi le variabili di ambiente della modalità esterna dal tuo file DockFlare `docker-compose.yml`.

```yaml
services:
  dockflare:
    image: alplat/dockflare:stable
    # ... other settings
    environment:
      # Remove the following two lines
      # - USE_EXTERNAL_CLOUDFLARED=true
      # - EXTERNAL_TUNNEL_ID=your-tunnel-uuid-goes-here
```

**Passaggio 2: implementa la modifica**

Esegui `docker compose up -d` per ricreare il contenitore DockFlare.

Quando viene avviato il contenitore DockFlare aggiornato:
1. Rileverà che `USE_EXTERNAL_CLOUDFLARED` è `false`.
2. **Creerà, configurerà e avvierà** automaticamente il proprio contenitore `cloudflared-agent` interno.
3. Configurerà questo nuovo agente per utilizzare il nome del tunnel definito nelle impostazioni di DockFlare.

**Passaggio 3: disattiva l'agente esterno**

Dopo aver confermato che il nuovo agente interno funziona correttamente e gestisce il traffico, puoi arrestare e rimuovere in tutta sicurezza il tuo agente `cloudflared`.
