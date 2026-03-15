# Utilizzo di più domini (etichette indicizzate)

DockFlare fornisce una potente funzionalità chiamata **etichette indicizzate** che ti consente di definire più regole ingress indipendenti per un singolo container. Ciò è particolarmente utile quando desideri esporre porte o percorsi diversi dello stesso servizio su nomi host pubblici diversi.

## Come funziona

Per creare più regole, è sufficiente anteporre alle etichette DockFlare standard un numero intero e un punto, a partire da `0`. Ad esempio, `dockflare.0.hostname`, `dockflare.1.hostname` e così via.

* Ogni indice (ad esempio, `0`, `1`, `2`) rappresenta una regola ingress separata.
* Per avviare una nuova regola è sempre necessario un nome host indicizzato (ad esempio, `dockflare.<index>.hostname`).
* Altre etichette nello stesso indice (ad esempio, `dockflare.<index>.service`) si applicheranno solo a quella regola specifica.

## Il meccanismo di fallback

Una caratteristica fondamentale delle etichette indicizzate è il meccanismo di fallback. Se non fornisci un'etichetta indicizzata specifica per una regola, questa **ripiegherà sul valore dell'etichetta base corrispondente (non indicizzata)**.

Ciò consente di definire le impostazioni comuni una volta al livello di base e di sovrascrivere solo i valori specifici che devono essere modificati per ciascuna regola indicizzata.

## Esempio: esposizione dell'interfaccia web e di un'API

Supponiamo che tu abbia un singolo container che serve sia un'applicazione web sulla porta `80` sia un'API separata sulla porta `3000`. Vuoi esporli rispettivamente su `app.example.com` e `api.example.com`. Vuoi anche proteggere l'API con un gruppo di accesso specifico, mentre l'app principale rimane pubblica.

Ecco come configurarlo utilizzando le etichette indicizzate:

```yaml
services:
  my-app:
    image: my-application
    restart: unless-stopped
    networks:
      - cloudflare-net
    labels:
      - "dockflare.enable=true"

      # --- Base Labels (Fallback) ---
      # This service is used by rule 0, as it's not specified there.
      - "dockflare.service=http://my-app:80" 

      # --- Rule 0: interfaccia web ---
      - "dockflare.0.hostname=app.example.com"
      # No 'service' label here, so it falls back to the base one.
      # No 'access.group' label, so it's public.

      # --- Rule 1: The API ---
      - "dockflare.1.hostname=api.example.com"
      # Override the service to point to the API port.
      - "dockflare.1.service=http://my-app:3000"
      # Add a specific access policy for this rule only.
      - "dockflare.1.access.group=api-users-policy"
```

### Scomposizione dell'esempio

* **Regola 0 (`app.example.com`)**:
    * Definisce `dockflare.0.hostname`.
    * Non definisce `dockflare.0.service`, quindi torna alla base `dockflare.service` e utilizza `http://my-app:80`.
    * È un servizio pubblico perché non è definita alcuna politica di accesso per questo indice o al livello base.

* **Regola 1 (`api.example.com`)**:
    * Definisce `dockflare.1.hostname`.
    * **Sostituisce** il servizio con `dockflare.1.service`, puntando alla porta API `3000`.
    * Applica una politica di sicurezza specifica utilizzando `dockflare.1.access.group`. Questa etichetta influisce solo su questa regola.

Questo approccio mantiene pulita la configurazione dell'etichetta ed evita ripetizioni, rendendo i tuoi file `docker-compose.yml` più facili da leggere e gestire.
