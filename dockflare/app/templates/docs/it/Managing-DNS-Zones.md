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
  # Questo servizio verrà creato nella zona predefinita (example.com)
  service-one:
    image: nginx
    labels:
      - "dockflare.enable=true"
      - "dockflare.hostname=nginx.example.com"
      - "dockflare.service=http://service-one:80"

  # Questo servizio verrà creato nella zona "media.io"
  service-two:
    image: portainer/portainer-ce
    labels:
      - "dockflare.enable=true"
      - "dockflare.hostname=portainer.media.io"
      - "dockflare.service=http://service-two:9000"
      # Sovrascrive la zona predefinita per questo servizio
      - "dockflare.zonename=media.io"
```

Quando lo distribuisci, DockFlare:
1. Crea un record CNAME per `nginx.example.com` nella zona `example.com`.
2. Crea un record CNAME per `portainer.media.io` nella zona `media.io`.

Entrambi i nomi host verranno aggiunti come regole ingress allo stesso tunnel Cloudflare.

## Visualizzazione dei record DNS nell'interfaccia web

La pagina **Impostazioni** dell'interfaccia web di DockFlare include una funzione che consente di visualizzare tutti i tunnel Cloudflare presenti nel tuo account e i record DNS che puntano a essi.

Per fare in modo che l'interfaccia web trovi i record DNS in tutte le zone, puoi utilizzare la variabile di ambiente `TUNNEL_DNS_SCAN_ZONE_NAMES`.

### `TUNNEL_DNS_SCAN_ZONE_NAMES`

Questa variabile di ambiente accetta un elenco di nomi di zona separati da virgole che DockFlare deve analizzare durante la ricerca dei record DNS.

**Esempio `docker-compose.yml`:**
```yaml
services:
  dockflare:
    image: alplat/dockflare:stable
    # ... other settings
    environment:
      # Fa analizzare all'interfaccia anche queste zone oltre a quella predefinita
      - TUNNEL_DNS_SCAN_ZONE_NAMES=media.io,another-domain.org
```

In questo modo il visualizzatore dei record DNS nell'interfaccia web mostrerà un quadro completo di tutti i domini che puntano ai tuoi tunnel.
