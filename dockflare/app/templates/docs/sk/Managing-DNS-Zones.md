# Správa DNS zón

DockFlare dokáže spravovať DNS záznamy naprieč viacerými doménami (Cloudflare zónami) v rámci toho istého Cloudflare účtu. Umožňuje ti to prevádzkovať služby na `service-a.domain-one.com` a `service-b.another-domain.org` z tej istej inštancie DockFlare.

## Predvolená zóna

Počas úvodného nastavenia DockFlare zadáš **Zone ID**. Je to **predvolená zóna**, kde bude DockFlare vytvárať všetky DNS záznamy. Ak plánuješ používať len jednu doménu, o nič viac sa nemusíš starať.

## Prepísanie zóny labelom

Na správu služby na inej doméne než predvolenej môžeš použiť label `dockflare.zonename`.

Tento label povie DockFlare, aby DNS záznam pre tú konkrétnu službu vytvoril v zadanej Cloudflare zóne.

### Predpoklady

Aby to fungovalo, musíš zabezpečiť, že **Cloudflare API token**, ktorý používaš, má oprávnenia `Zone:DNS:Edit` pre **všetky zóny**, ktoré chceš spravovať.

### Príklad

Povedzme, že tvoja predvolená zóna je `example.com`, no chceš prevádzkovať službu aj na `media.io`.

```yaml
services:
  # Táto služba sa vytvorí v predvolenej zóne (example.com)
  service-one:
    image: nginx
    labels:
      - "dockflare.enable=true"
      - "dockflare.hostname=nginx.example.com"
      - "dockflare.service=http://service-one:80"

  # Táto služba sa vytvorí v zóne 'media.io'
  service-two:
    image: portainer/portainer-ce
    labels:
      - "dockflare.enable=true"
      - "dockflare.hostname=portainer.media.io"
      - "dockflare.service=http://service-two:9000"
      # Prepíš predvolenú zónu pre túto službu
      - "dockflare.zonename=media.io"
```

Keď to nasadíš, DockFlare:
1.  Vytvorí CNAME záznam pre `nginx.example.com` v zóne `example.com`.
2.  Vytvorí CNAME záznam pre `portainer.media.io` v zóne `media.io`.

Oba hostname sa pridajú ako ingress pravidlá do toho istého Cloudflare tunela.

## Zobrazenie DNS záznamov v UI

Webové rozhranie DockFlare má na stránke **Nastavenia** funkciu, ktorá ti umožní zobraziť všetky Cloudflare tunely na tvojom účte a DNS záznamy, ktoré na ne smerujú.

Aby UI dokázalo nájsť DNS záznamy naprieč všetkými tvojimi zónami, môžeš použiť premennú prostredia `TUNNEL_DNS_SCAN_ZONE_NAMES`.

### `TUNNEL_DNS_SCAN_ZONE_NAMES`

Táto premenná prostredia prijíma čiarkou oddelený zoznam názvov zón, ktoré má UI prehľadať pri hľadaní DNS záznamov.

**Príklad `docker-compose.yml`:**
```yaml
services:
  dockflare:
    image: alplat/dockflare:stable
    # ... ďalšie nastavenia
    environment:
      # Povedz UI, aby okrem predvolenej prehľadalo aj tieto zóny
      - TUNNEL_DNS_SCAN_ZONE_NAMES=media.io,another-domain.org
```

Zabezpečí to, že prehliadač DNS záznamov v UI poskytne kompletný obraz o všetkých doménach smerujúcich na tvoje tunely.
