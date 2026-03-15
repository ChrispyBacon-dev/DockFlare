# Utilizzo di domini wildcard

DockFlare supporta l'utilizzo di domini con wildcard (ad esempio, `*.example.com`) per instradare il traffico per più sottodomini a un singolo servizio. Ciò è particolarmente utile per le applicazioni che gestiscono sottodomini dinamici, come servizi multi-tenant o dashboard personali come Heimdall.

## Come funziona

Quando utilizzi un nome host con wildcard, Cloudflare Tunnel instraderà tutto il traffico per qualsiasi sottodominio che non dispone di un record DNS più specifico al servizio specificato.

Ad esempio, se configuri `*.apps.example.com`, il traffico per `service1.apps.example.com`, `service2.apps.example.com` e così via verrà tutto instradato allo stesso contenitore di destinazione.

## Considerazioni importanti

A differenza dei normali nomi host, DockFlare **non può creare automaticamente record DNS per domini con wildcard**. È necessario creare manualmente il record DNS con wildcard nella dashboard di Cloudflare.

DockFlare gestirà comunque la **regola ingress** nel tuo tunnel Cloudflare, ma la configurazione DNS iniziale è un passaggio manuale.

## Guida passo passo

Ecco come impostare correttamente un dominio wildcard con DockFlare, utilizzando `*.plex.example.com` come esempio.

### Passaggio 1: crea manualmente il record DNS con wildcard

1. Accedi alla tua **Dashboard di Cloudflare**.
2. Vai alle impostazioni DNS per il tuo dominio.
3. Fai clic su **Aggiungi record** e crea un record CNAME con i seguenti dettagli:
    * **Digitare:** `CNAME`
    * **Nome:** `*.plex` (o solo `*` se il tuo dominio principale è `plex.example.com`)
    * **Destinazione:** il nome host pubblico del tuo tunnel. Puoi trovarlo nella dashboard di Cloudflare Zero Trust in **Accesso -> Tunnel**. Assomiglierà a qualcosa come `your-tunnel-uuid.cfargotunnel.com`.
    * **Stato proxy:** Assicurati che sia **Proxied** (nuvola arancione).

    Questo record DNS manuale indica a Cloudflare di inviare tutto il traffico per `*.plex.example.com` al tuo tunnel.

### Passaggio 2: configura il tuo servizio con un'etichetta wildcard

Ora configura il tuo servizio nel file `docker-compose.yml` con un'etichetta del nome host con wildcard.

```yaml
services:
  my-proxy-manager:
    image: nginxproxymanager/nginx-proxy-manager
    restart: unless-stopped
    networks:
      - cloudflare-net
    labels:
      - "dockflare.enable=true"
      # Usa qui il nome host con wildcard
      - "dockflare.hostname=*.plex.example.com"
      - "dockflare.service=http://my-proxy-manager:81"
```

### Passaggio 3: distribuzione e verifica

1. Salva il tuo file `docker-compose.yml` ed esegui `docker compose up -d`.
2. DockFlare rileverà il container e creerà una regola ingress nel tuo tunnel Cloudflare per il nome host `*.plex.example.com`.
3. Puoi verificarlo nell'interfaccia web di DockFlare e nella configurazione del tunnel nella dashboard di Cloudflare.

Ora, qualsiasi richiesta a un sottodominio come `sonarr.plex.example.com` o `radarr.plex.example.com` verrà instradata attraverso il tuo tunnel Cloudflare al tuo contenitore `my-proxy-manager`, che potrà quindi gestire il traffico di conseguenza.
