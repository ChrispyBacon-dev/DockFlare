# Kontroly stavu

DockFlare obsahuje vyhradený health check endpoint, ktorý sa dá použiť so zabudovaným mechanizmom kontroly stavu v Dockeri. Umožňuje Dockeru sledovať stav aplikácie DockFlare a automaticky ju reštartovať, ak prestane odpovedať.

## Endpoint `/ping`

DockFlare vystavuje jednoduchý HTTP endpoint na `/ping`.

*   **Účel:** Poskytnúť automatizovaným systémom jednoduchý spôsob, ako overiť, či webový server DockFlare beží a odpovedá.
*   **Overovanie:** Tento endpoint je **oslobodený od overovania**. Na prístup k nemu nemusíš byť prihlásený, čo umožňuje jeho použitie interným mechanizmom kontroly stavu v Dockeri.
*   **Odpoveď pri dobrom stave:** Zdravá, bežiaca aplikácia DockFlare odpovie na požiadavku na `/ping` stavovým kódom **HTTP 200 OK**.
*   **Informácia o verzii:** Telo odpovede z endpointu `/ping` obsahuje aj bežiacu verziu aplikácie DockFlare.

## Ako nastaviť kontrolu stavu v Docker Compose

Do služby `dockflare` v súbore `docker-compose.yml` môžeš pridať sekciu `healthcheck`, aby Docker automaticky sledoval stav aplikácie.

```yaml
services:
  dockflare:
    image: alplat/dockflare:stable
    container_name: dockflare
    restart: unless-stopped
    # ... ďalšie nastavenia
    healthcheck:
      # Príkaz na kontrolu stavu.
      # wget je dostupný v image DockFlare a kontroluje ping endpoint.
      test: ["CMD", "wget", "--no-verbose", "--tries=1", "--spider", "http://localhost:5000/ping"]
      # Ako často spúšťať kontrolu
      interval: 1m30s
      # Ako dlho čakať na odpoveď
      timeout: 10s
      # Koľko po sebe idúcich zlyhaní pred označením ako nezdravé
      retries: 3
      # Ako dlho čakať po spustení kontajnera pred prvou kontrolou
      start_period: 40s
```

### Rozbor konfigurácie `healthcheck`:

*   `test`: Príkaz, ktorý Docker spúšťa vnútri kontajnera. `wget --spider` vykoná HTTP požiadavku na endpoint `/ping` a skončí s nenulovým stavovým kódom, ak odpoveď nie je HTTP 200 OK.
*   `interval`: Docker spustí túto kontrolu každých 90 sekúnd.
*   `timeout`: Docker počká na dokončenie príkazu až 10 sekúnd.
*   `retries`: Ak kontrola zlyhá 3-krát po sebe, Docker označí kontajner ako `unhealthy`.
*   `start_period`: Docker po spustení kontajnera počká 40 sekúnd pred prvou kontrolou stavu. Aplikácia tak dostane čas na správnu inicializáciu.

S touto konfiguráciou môžeš skontrolovať stav svojho kontajnera spustením `docker ps`. Stĺpec so stavom zobrazí `(healthy)`, ak kontrola prechádza. Ak sa kontajner stane nezdravým, Docker ho automaticky reštartuje podľa politiky `restart` (napr. `unless-stopped`).
