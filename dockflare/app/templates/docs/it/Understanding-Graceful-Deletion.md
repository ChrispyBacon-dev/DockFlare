# Comprendere la cancellazione automatica

Quando interrompi un contenitore gestito da DockFlare, potresti notare che il nome host pubblico corrispondente non va immediatamente offline. Ciò è dovuto a una funzionalità chiamata **Graceful Deletion**.

## Che cos'è la Graceful Deletion?

Invece di eliminare istantaneamente la regola ingress di Cloudflare e il record DNS nel momento in cui un container si ferma, DockFlare contrassegna la regola come **"in attesa di eliminazione"** e avvia un timer.

Le risorse Cloudflare associate (la regola ingress e il record DNS) verranno eliminate in modo permanente solo dopo la scadenza di questo timer, noto come **periodo di grazia**.

## Perché è utile?

Questa funzionalità è progettata per prevenire interruzioni del servizio in scenari operativi comuni:

* **Aggiornamenti del container:** quando aggiorni un'immagine del container (`docker compose up -d`), Docker in genere arresta il vecchio container e ne avvia uno nuovo. Senza un periodo di grazia, il tuo servizio sarebbe inaccessibile per un breve periodo. Con la Graceful Deletion, il record DNS e la regola ingress rimangono attivi e DockFlare li riassocia semplicemente al nuovo container, con tempi di inattività pari a zero.
* **Riavvii temporanei:** se è necessario arrestare un container per un momento per modificare un'impostazione e quindi riavviarlo, il periodo di grazia garantisce che la configurazione rivolta al pubblico rimanga intatta.

## La variabile `GRACE_PERIOD_SECONDS`

La durata di questo periodo di grazia è controllata dalla variabile di ambiente `GRACE_PERIOD_SECONDS`, che puoi impostare nel tuo file `docker-compose.yml`.

* Il valore predefinito è `600` secondi (10 minuti).
* È possibile modificare questo valore in base alle proprie esigenze. Un periodo più breve velocizza la pulizia, mentre un periodo più lungo fornisce una finestra più ampia per il riavvio del contenitore.

**Esempio:**
```yaml
services:
  dockflare:
    image: alplat/dockflare:stable
    # ... other settings
    environment:
      - GRACE_PERIOD_SECONDS=3600 # Set a 1-hour grace period
```

## Come funziona nella pratica

1. **Contenitore arrestato:** esegui `docker stop my-app`.
2. **In attesa di eliminazione:** DockFlare rileva l'evento di interruzione. Nell'interfaccia web, la regola per `my-app.example.com` mostrerà ora lo stato **"pending_deletion"** insieme all'orario previsto per l'eliminazione.
3. **I due scenari:**
    * **Scenario A: il periodo di tolleranza scade:** se il container rimane fermo e il periodo di tolleranza (ad esempio, 10 minuti) scade, verrà eseguita l'attività di pulizia in background di DockFlare. Eliminerà la regola ingress dal tuo tunnel Cloudflare e rimuoverà il record DNS CNAME.
    * **Scenario B: riavvio del container:** se si avvia nuovamente il container (`docker start my-app`) **prima** della scadenza del periodo di grazia, DockFlare rileverà l'evento di avvio. Vedrà che la regola è in attesa di eliminazione, annullerà l'eliminazione e modificherà il suo stato nuovamente in **"attiva"**. Il tuo servizio continua a funzionare senza problemi.
