# Agent DockFlare a viacserverová architektúra

DockFlare 3.0 zavádza model distribuovaného vykonávania, ktorý ti umožní spravovať Cloudflare tunely naprieč viacerými Docker hostiteľmi. DockFlare **Master** koordinuje konfiguráciu, kým odľahčení **agenti** bežia popri tvojich záťažiach a udržiavajú svoju lokálnu inštanciu `cloudflared` zosynchronizovanú s Masterom.

Táto príručka vysvetľuje architektúru, bezpečnostný model a postup nasadenia agentov krok za krokom.

---

## Prečo agenti?

* **Oddelenie výpočtu od ingress** – udrž záťaže blízko používateľov, kým máš jednu riadiacu rovinu.
* **Viditeľnosť na úrovni hostiteľa** – sleduj heartbeat, stav tunela a históriu príkazov pre každého agenta.
* **Tokeny s najmenšími oprávneniami** – zneplatni kompromitovaných agentov bez zásahu do Mastera či iných hostiteľov.
* **Odolné aktualizácie** – agenti pokračujú v obsluhe prevádzky so svojou poslednou známou konfiguráciou, ak je Master dočasne nedostupný.

---

## Komponenty v skratke

| Komponent | Zodpovednosť |
|-----------|----------------|
| **Master (DockFlare)** | Hostuje webové UI, ukladá stav, synchronizuje požadované ingress pravidlá, vydáva príkazy. |
| **Redis** | Backplane pre cachovanie, heartbeaty agentov a zaradené príkazy. |
| **DockFlare agent** | Bezhlavý kontajner, ktorý sleduje lokálne Docker udalosti, vykonáva príkazy a spúšťa `cloudflared`. |
| **cloudflared** | Zabezpečuje samotné tunelové spojenie s Cloudflare pre každého agenta. |

Master a Redis zvyčajne bežia spolu, kým agenti bežia popri záťažiach (potenciálne na vzdialených sieťach).

---

## Predpoklady

* DockFlare Master ≥ v3.0 s nakonfigurovaným Redisom (nastavené `REDIS_URL`). Voliteľne zadaj `REDIS_DB_INDEX` na izoláciu dát od iných kontajnerov používajúcich tú istú Redis inštanciu.
* Cloudflare API token s oprávneniami Tunnel + Access (rovnako ako v predchádzajúcich verziách).
* Docker runtime na každom hostiteľovi, ktorého plánuješ spravovať.
* (Voliteľné) Vyhradený sieťový segment alebo VPN medzi Masterom a agentmi, ak Master nevystavuješ verejne.

---

## Prehľad pracovného postupu

1. **Vygeneruj API kľúč agenta** v UI DockFlare (`Agenti → Generovať kľúč`).
2. **Nasaď kontajner DockFlare agent** na vzdialenom hostiteľovi, s odovzdaním URL Mastera a kľúča.
3. Agent sa **zaregistruje** u Mastera a zobrazí sa so stavom *Čaká*.
4. V UI Mastera agenta **zaregistruj** – priraď alebo vytvor Cloudflare tunel pre daného hostiteľa.
5. Master zaradí príkazy; agent **dopytuje**, uplatní konfiguráciu a hlási stav/heartbeat. DockFlare automaticky zistí cieľovú zónu pre každý hostname (k predvolenej zóne sa uchýli len vtedy, keď detekcia zlyhá).
6. Keď sa na hostiteľovi agenta spúšťajú/zastavujú kontajnery, agent streamuje udalosti späť Masteru, ktorý aktualizuje DNS, Access politiky a ingress pravidlá tunela.

---

## Nasadenie DockFlare agenta

Agent je publikovaný ako `alplat/dockflare-agent:latest` na Docker Hube.

Existujú dve metódy nasadenia — vyber si tú, ktorá vyhovuje tvojmu nastaveniu:

### Možnosť A — Jednoriadkový deploy skript (odporúčané, opt-in)

Ak si na Masteri nakonfiguroval **Cloudflare Zero Trust** (`Agenti → Nastaviť Zero Trust`), DockFlare dokáže pre každý API kľúč agenta vygenerovať plne predkonfigurovaný bash skript. Skript:

- Skontroluje, či je dostupné `docker compose`
- Vytvorí Docker sieť `cloudflare-net`, ak neexistuje
- Zapíše `docker-compose.yml` so všetkými štyrmi potrebnými hodnotami zapečenými dovnútra (`DOCKFLARE_MASTER_URL`, `DOCKFLARE_API_KEY`, `CF_ACCESS_CLIENT_ID`, `CF_ACCESS_CLIENT_SECRET`)
- Okamžite spustí stack agenta

Použitie: prejdi na `Agenti → (riadok kľúča) → Nasadiť agenta → Rýchle nasadenie`, skopíruj skript a vlož ho do SSH relácie na cieľovom serveri. Netreba nastavovať `.env` súbor.

> Táto možnosť vyžaduje, aby bola na Masteri nakonfigurovaná funkcia Cloudflare Zero Trust. Podrobnosti nájdeš v sekcii [Bezpečnostný model](#bezpecnostny-model).

### Možnosť B — Manuálne nastavenie compose

Pre prostredia, kde si spravuješ vlastné konfiguračné súbory:

```bash
# .env na hostiteľovi agenta
DOCKFLARE_MASTER_URL=https://dockflare.example.com
DOCKFLARE_API_KEY=agent_api_key_goes_here
DOCKER_HOST=tcp://docker-socket-proxy:2375
# Voliteľné: pripni cloudflared image (prijíma repo:tag alebo repo@sha256:<digest>)
# Predvolene cloudflare/cloudflared:latest, keď nie je nastavené
CLOUDFLARED_IMAGE=cloudflare/cloudflared:latest
LOG_LEVEL=info
TZ=Europe/Zurich
# Voliteľné: Cloudflare Zero Trust service token (vygenerovaný Masterom)
CF_ACCESS_CLIENT_ID=
CF_ACCESS_CLIENT_SECRET=
```

Minimálny `docker-compose.yml` na hostiteľovi agenta:

```yaml
services:
  docker-socket-proxy:
    image: tecnativa/docker-socket-proxy:v0.4.1
    container_name: docker-socket-proxy
    restart: unless-stopped
    environment:
      - DOCKER_HOST=unix:///var/run/docker.sock
      - CONTAINERS=1
      - EVENTS=1
      - NETWORKS=1
      - IMAGES=1
      - POST=1
      - PING=1
      - EXEC=1
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock
    networks:
      - dockflare-internal

  dockflare-agent:
    image: alplat/dockflare-agent:latest
    container_name: dockflare-agent
    restart: unless-stopped
    env_file:
      - .env
    environment:
      - DOCKER_HOST=${DOCKER_HOST:-tcp://docker-socket-proxy:2375}
      - TZ=${TZ:-UTC}
      - LOG_LEVEL=${LOG_LEVEL:-info}
    volumes:
      - agent_data:/app/data
    depends_on:
      - docker-socket-proxy
    networks:
      - cloudflare-net
      - dockflare-internal

volumes:
  agent_data:

networks:
  cloudflare-net:
    name: cloudflare-net
    external: true
  dockflare-internal:
    name: dockflare-internal
```

- Raz spusti `docker network create cloudflare-net` na pripravenie zdieľanej siete používanej Masterom a agentmi.
- Socket proxy obmedzuje plochu Docker API, ku ktorej agent dosiahne; vystavené sú len schopnosti nastavené na `1`.
- Image agenta beží ako neprivilegovaný používateľ `dockflare` (UID/GID 65532). Zabezpeč, aby boli pripojené adresáre ako `/app/data` zapisovateľné týmto účtom.
- Vyplň súbor `.env` minimálne s `DOCKFLARE_MASTER_URL` a `DOCKFLARE_API_KEY`; všetky ostatné premenné sú voliteľné prepisy.

---

## Bezpečnostný model

* **Master API kľúč** – chráni administrátorské API. UI ho odhalí až po kliknutí na *Zobraziť master API kľúč*.
* **API kľúče agentov** – jedinečné pre každého agenta. Zneplatnenie kľúča okamžite zablokuje ďalšiu registráciu/príkazy z daného hostiteľa.
* **Cloudflare Zero Trust service tokeny** *(opt-in)* – keď sú nakonfigurované, DockFlare vytvorí Cloudflare Access aplikáciu ohraničenú na `/api/v2/agents/` s politikou `non_identity`. Agenti pri každej požiadavke predložia hlavičky `CF-Access-Client-Id` a `CF-Access-Client-Secret`, ktoré Cloudflare overí na edge ešte predtým, než prevádzka dosiahne Master. Pridáva to druhú vrstvu overovania nad API kľúč agenta. Prístup admina cez prehliadač naďalej funguje cez politiku `bypass` na tej istej aplikácii. Zapni to cez `Agenti → Nastaviť Zero Trust`.
* **Redis** – používaný na fronty a cache; zabezpeč ho (heslo + sieťové ACL), ak beží mimo dôveryhodnej LAN.
* **Prenos** – prevádzkuj Master za HTTPS (napr. cez Cloudflare Tunnel), aby bola prevádzka agentov pri prenose šifrovaná.
* **Beh s najmenšími oprávneniami** – kontajner agenta beží ako používateľ `dockflare` (UID/GID 65532) a spolieha sa na socket proxy, aby udržal prístup k Dockeru ohraničený na inšpekciu kontajnerov a riadenie ich životného cyklu.

### Odporúčané spevnenie

1. Ukladaj kľúče agentov vo vaulte/správcovi hesiel; pravidelne ich rotuj.
2. Zapni **Cloudflare Zero Trust** na Masteri pre ďalšiu vrstvu overovania na Cloudflare edge (`Agenti → Nastaviť Zero Trust`).
3. **Nevypínaj prihlasovanie heslom** – namiesto toho použi OAuth/OIDC providerov pre pohodlie single sign-on bez bezpečnostných rizík. Ak musíš prihlasovanie heslom vypnúť, uvedom si, že to vytvára zraniteľnosť Docker siete, kde ktorýkoľvek kontajner na tej istej sieti môže obísť externé overovanie. Úplné bezpečnostné dôsledky nájdeš v [Prístup k webovému rozhraniu – Vypnutie prihlasovania heslom](Accessing-the-Web-UI.md#vypnutie-prihlasovania-heslom).
4. Používaj samostatné tunely pre každého agenta pre izoláciu s najmenšími oprávneniami.
5. Sleduj stránku `Agenti` na medzery v heartbeatoch – offline uzly možno odstrániť priamo z UI.

---

## Riešenie problémov

| Príznak | Riešenie |
|---------|-----|
| Agent uviaznutý v `pending` | Uisti sa, že sa zaregistroval so správnym API kľúčom, a zaregistruj ho z UI. |
| Príkazy sa nikdy nevyčistia | Over pripojenie k Redisu a či sú hodiny kontajnera agenta zosynchronizované. |
| DNS sa neaktualizuje | Master musí dosiahnuť Cloudflare a agent musí posielať udalosti kontajnerov; over `docker logs dockflare-agent`. |
| Heartbeat offline | Skontroluj sieťovú cestu medzi agentom a Masterom; časté príčiny sú problémy s firewallom alebo TLS. |

---

## Ďalšie kroky

* Prezri si Rýchly štart v README repozitára, aby si sa uistil, že Redis je nakonfigurovaný.
* Skontroluj changelog na prelomové zmeny a poznámky k migrácii.
* Zváž zapnutie Cloudflare Zero Trust pre spevnené overovanie agentov (`Agenti → Nastaviť Zero Trust`).

Šťastné tunelovanie! 🚇
