# Použitie viacerých domén (indexované labely)

DockFlare ponúka výkonnú funkciu nazvanú **indexované labely**, ktorá ti umožní definovať pre jeden kontajner viacero nezávislých ingress pravidiel. Hodí sa to najmä vtedy, keď chceš vystaviť rôzne porty alebo cesty tej istej služby na rôznych verejných hostname.

## Ako to funguje

Na vytvorenie viacerých pravidiel jednoducho pred štandardné DockFlare labely pridáš celé číslo a bodku, počnúc `0`. Napríklad `dockflare.0.hostname`, `dockflare.1.hostname` a tak ďalej.

*   Každý index (napr. `0`, `1`, `2`) predstavuje samostatné ingress pravidlo.
*   Indexovaný hostname (napr. `dockflare.<index>.hostname`) je vždy potrebný na začatie nového pravidla.
*   Ostatné labely pri rovnakom indexe (napr. `dockflare.<index>.service`) sa uplatnia len na to konkrétne pravidlo.

## Mechanizmus záložnej hodnoty

Kľúčovou vlastnosťou indexovaných labelov je mechanizmus záložnej hodnoty (fallback). Ak pre pravidlo neposkytneš konkrétny indexovaný label, **použije sa hodnota zodpovedajúceho základného (neindexovaného) labelu**.

Umožňuje ti to definovať spoločné nastavenia raz na základnej úrovni a prepísať len tie konkrétne hodnoty, ktoré sa pri každom indexovanom pravidle musia zmeniť.

## Príklad: Vystavenie webového UI a API

Povedzme, že máš jeden kontajner, ktorý obsluhuje webovú aplikáciu na porte `80` aj samostatné API na porte `3000`. Chceš ich vystaviť na `app.example.com` a `api.example.com`. API chceš zároveň zabezpečiť konkrétnou prístupovou skupinou, kým hlavná aplikácia zostane verejná.

Takto by si to nakonfiguroval pomocou indexovaných labelov:

```yaml
services:
  my-app:
    image: my-application
    restart: unless-stopped
    networks:
      - cloudflare-net
    labels:
      - "dockflare.enable=true"

      # --- Základné labely (fallback) ---
      # Túto službu použije pravidlo 0, keďže tam nie je zadaná.
      - "dockflare.service=http://my-app:80"

      # --- Pravidlo 0: Webové UI ---
      - "dockflare.0.hostname=app.example.com"
      # Žiadny label 'service', takže sa použije základný.
      # Žiadny label 'access.group', takže je verejné.

      # --- Pravidlo 1: API ---
      - "dockflare.1.hostname=api.example.com"
      # Prepíš službu tak, aby ukazovala na port API.
      - "dockflare.1.service=http://my-app:3000"
      # Pridaj konkrétnu prístupovú politiku len pre toto pravidlo.
      - "dockflare.1.access.group=api-users-policy"
```

### Rozbor príkladu

*   **Pravidlo 0 (`app.example.com`)**:
    *   Definuje `dockflare.0.hostname`.
    *   Nedefinuje `dockflare.0.service`, takže sa použije základný `dockflare.service` a použije `http://my-app:80`.
    *   Je to verejná služba, keďže pre tento index ani na základnej úrovni nie je definovaná žiadna prístupová politika.

*   **Pravidlo 1 (`api.example.com`)**:
    *   Definuje `dockflare.1.hostname`.
    *   **Prepisuje** službu cez `dockflare.1.service` a ukazuje na port API `3000`.
    *   Uplatňuje konkrétnu bezpečnostnú politiku cez `dockflare.1.access.group`. Tento label ovplyvňuje len toto pravidlo.

Tento prístup udrží konfiguráciu labelov prehľadnú a bez opakovania, vďaka čomu sú tvoje súbory `docker-compose.yml` čitateľnejšie a ľahšie udržiavateľné.
