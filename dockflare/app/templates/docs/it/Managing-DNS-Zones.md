# Gestione delle zone DNS

DockFlare è in grado di gestire record DNS su più domini (zone Cloudflare) all'interno dello stesso account Cloudflare. Ciò ti consente di eseguire servizi su `service-a.domain-one.com` e `service-b.another-domain.org` dalla stessa istanza DockFlare.

## Zona predefinita

Durante la configurazione iniziale di DockFlare, fornisci un **ID zona**. Questa è la **zona predefinita** in cui DockFlare creerà tutti i record DNS. Se prevedi di utilizzare un solo dominio, questo è tutto ciò di cui devi preoccuparti.

## Sovrascrivere la zona con un'etichetta

Per gestire un servizio su un dominio diverso da quello predefinito puoi utilizzare l'etichetta `dockflare.zonename`.

Questa etichetta indica a DockFlare di creare il record DNS per quello specifico servizio nella zona Cloudflare specificata.

### Prerequisiti

Affinché funzioni, devi assicurarti che il **token API Cloudflare** che stai utilizzando disponga delle autorizzazioni `Zone:DNS:Edit` per **tutte le zone** che intendi gestire.

### Esempio

Supponiamo che la tua zona predefinita sia `example.com`, ma desideri anche eseguire un servizio su `media.io`.

```yaml
services:
  # This service will be created in the default zone (example.com)
  service-one:
    image: nginx
    labels:
      - "dockflare.enable=true"
      - "dockflare.hostname=nginx.example.com"
      - "dockflare.service=http://service-one:80"

  # This service will be created in the 'media.io' zone
  service-two:
    image: portainer/portainer-ce
    labels:
      - "dockflare.enable=true"
      - "dockflare.hostname=portainer.media.io"
      - "dockflare.service=http://service-two:9000"
      # Override the default zone for this service
      - "dockflare.zonename=media.io"
```

Quando lo distribuisci, DockFlare:
1. Crea un record CNAME per `nginx.example.com` nella zona `example.com`.
2. Crea un record CNAME per `portainer.media.io` nella zona `media.io`.

Entrambi i nomi host verranno aggiunti come regole ingress allo stesso tunnel Cloudflare.

## Visualizzazione dei record DNS nella Web UI

La Web UI di DockFlare include una funzionalità nella pagina **Impostazioni** che ti consente di visualizzare tutti i tunnel Cloudflare sul tuo account e i record DNS che puntano ad essi.

Per garantire che la Web UI possa trovare i record DNS in tutte le diverse zone, puoi utilizzare la variabile di ambiente `TUNNEL_DNS_SCAN_ZONE_NAMES`.

### `TUNNEL_DNS_SCAN_ZONE_NAMES`

Questa variabile di ambiente accetta un elenco separato da virgole di nomi di zone che la Web UI deve analizzare durante la ricerca di record DNS.

**Esempio `docker-compose.yml`:**
```yaml
services:
  dockflare:
    image: alplat/dockflare:stable
    # ... other settings
    environment:
      # Tell the UI to scan these zones in addition to the default one
      - TUNNEL_DNS_SCAN_ZONE_NAMES=media.io,another-domain.org
```

Ciò garantirà che il visualizzatore di record DNS nella Web UI fornisca un quadro completo di tutti i domini che puntano ai tuoi tunnel.
