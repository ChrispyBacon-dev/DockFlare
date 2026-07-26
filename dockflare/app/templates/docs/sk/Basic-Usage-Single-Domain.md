# Základné použitie (jedna doména)

Táto príručka demonštruje najbežnejší prípad použitia DockFlare: vystavenie jedného Docker kontajnera do internetu na verejnom hostname.

## Predpoklady

Skôr než začneš, uisti sa, že máš:
1.  Dokončenú príručku [Rýchly štart](Quick-Start-Docker-Compose.md).
2.  DockFlare beží a je pripojený k tvojmu Cloudflare účtu.
3.  Máš službu, ktorú chceš vystaviť (v tomto príklade použijeme `nginx`).

## Príklad: Vystavenie NGINX kontajnera

Povedzme, že chceš vystaviť štandardný NGINX webový server na hostname `nginx.example.com`.

### 1. Pridaj službu do svojho `docker-compose.yml`

Uprav súbor `docker-compose.yml` tak, aby zahŕňal službu `nginx`. Kľúčové je pridať do jej konfigurácie labely `dockflare.*`.

```yaml
version: '3.8'

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
      - INFO=1
      - EXEC=1
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock
    networks:
      - dockflare-internal

  dockflare-init:
    image: alpine:3.20
    command: ["sh", "-c", "chown -R 65532:65532 /app/data"]
    volumes:
      - dockflare_data:/app/data
    networks:
      - dockflare-internal
    restart: "no"

  dockflare:
    image: alplat/dockflare:stable
    container_name: dockflare
    restart: unless-stopped
    ports:
      - "5000:5000"
    volumes:
      - dockflare_data:/app/data
    environment:
      - REDIS_URL=redis://redis:6379/0
      - REDIS_DB_INDEX=0  # Voliteľné: zadaj index Redis databázy (0-15) na izoláciu od iných kontajnerov
      - DOCKER_HOST=tcp://docker-socket-proxy:2375
    depends_on:
      docker-socket-proxy:
        condition: service_started
      dockflare-init:
        condition: service_completed_successfully
      redis:
        condition: service_started
    networks:
      - cloudflare-net
      - dockflare-internal

  # Sem pridaj svoju novú službu
  nginx-webserver:
    image: nginx:latest
    container_name: my-nginx
    restart: unless-stopped
    networks:
      - cloudflare-net
    labels:
      - "dockflare.enable=true"
      - "dockflare.hostname=nginx.example.com"
      - "dockflare.service=http://nginx-webserver:80"
      # Voliteľné: Uplatni verejný prístup s obídením ochrany zóny
      - "dockflare.access.group=public-default-bypass"

  redis:
    image: redis:7-alpine
    container_name: dockflare-redis
    restart: unless-stopped
    command: ["redis-server", "--save", "", "--appendonly", "no"]
    volumes:
      - dockflare_redis:/data
    networks:
      - dockflare-internal

volumes:
  dockflare_data:
  dockflare_redis:

networks:
  cloudflare-net:
    name: cloudflare-net
    external: true
  dockflare-internal:
    name: dockflare-internal
```
> **Prečo Redis?** DockFlare sa spolieha na Redis pri cachovaní, streamovaní logov a správach medzi vláknami. Jeho prevádzka na privátnej sieti `dockflare-internal` zabezpečí, že Redis je dostupný len pre DockFlare, kým záťaže zostávajú izolované na `cloudflare-net`.


### 2. Pochopenie labelov

*   `dockflare.enable=true`: Toto povie DockFlare, aby tento kontajner spravoval.
*   `dockflare.hostname=nginx.example.com`: Toto je verejná URL, kde bude tvoja služba dostupná. DockFlare vytvorí pre tento hostname DNS záznam v tvojom Cloudflare účte.
*   `dockflare.service=http://nginx-webserver:80`: Toto povie Cloudflare Tunnelu, kam posielať prevádzku. Je to interná adresa NGINX kontajnera. Všimni si, že ako hostname používame názov služby (`nginx-webserver`), čo je možné, keďže oba kontajnery sú na tej istej Docker sieti.
*   `dockflare.access.group=public-default-bypass`: (Voliteľné) Používa systémovú bypass politiku na zabezpečenie verejného prístupu aj vtedy, keď existuje ochranná politika na úrovni zóny `*.example.com`. Je to dôležité, keď máš wildcard politiky chrániace tvoju doménu, no potrebuješ, aby konkrétne služby zostali verejné.

### 3. Nasaď službu

Ulož súbor `docker-compose.yml` a spusti tento príkaz na spustenie novej služby:

```bash
docker compose up -d
```

### 4. Overenie

DockFlare zaznamená nový kontajner a automaticky vykoná tieto akcie:
1.  Pridá ingress pravidlo do tvojho Cloudflare tunela pre `nginx.example.com`.
2.  Vytvorí CNAME záznam pre `nginx.example.com` v tvojom Cloudflare DNS, ktorý smeruje na tunel.

Over si to niekoľkými spôsobmi:
*   **Webové rozhranie DockFlare**: Služba `nginx.example.com` sa zobrazí na dashboarde.
*   **Cloudflare dashboard**: Uvidíš nový CNAME záznam v nastaveniach DNS a nové ingress pravidlo v konfigurácii svojho tunela.

Po chvíli, potrebnej na propagáciu DNS, by si mal vedieť v prehliadači prejsť na `https://nginx.example.com` a vidieť predvolenú uvítaciu stránku NGINX.

## Detailný pohľad na zálohu a obnovenie

DockFlare prichádza s prvotriednym zálohovacím postupom, takže inštanciu presunieš alebo obnovíš v priebehu minút.

### Čo obsahuje zálohovací archív

Keď si stiahneš zálohu z **Nastavenia → Záloha a obnovenie** (alebo úvodného sprievodcu), DockFlare vygeneruje `.zip` s týmito súbormi:

| Súbor | Popis |
| --- | --- |
| `dockflare_config.dat` | Zašifrovaný konfiguračný payload (Cloudflare prihlasovacie údaje, haš UI hesla, predvolené hodnoty tunela, hlavný API kľúč atď.). |
| `dockflare.key` | Fernet kľúč použitý na dešifrovanie `dockflare_config.dat` a ďalších zašifrovaných payloadov. Drž ho spolu s archívom. |
| `agent_keys.dat` | Zašifrovaný register API kľúčov agentov, metadát a stavu zneplatnenia. |
| `state.json` | Čitateľná JSON snímka runtime stavu — spravované pravidlá, agenti, prístupové skupiny. Je zahrnutá, aby operátori mohli v prípade potreby skúmať alebo migrovať konkrétne časti. |
| `manifest.json` | Kontrolné súčty a informácie o verzii pre každý súbor v archíve. |

Záloha je samostatná: jej obnovenie cez sprievodcu/apply endpoint zapíše každý súbor do `/app/data/` a okamžite naplánuje reštart kontajnera, aby sa zašifrovaná konfigurácia pri štarte znovu načítala.

### Poznámky k obnoveniu a kompatibilite

- **Sprievodca a UI Nastavenia**: Nahraj `.zip` a DockFlare ho naimportuje, znovu načíta stav a ukončí sa. Docker kontajner automaticky reštartuje, takže sa vrátiš do prevádzkového režimu bez manuálneho zásahu.
- **Starší `state.json`**: Na riešenie problémov alebo pokročilé workflowy môžeš stále nahrať len súbor `state.json`. DockFlare z neho naplní runtime stav, no preskočí zašifrovanú konfiguráciu; prihlasovacie údaje potom musíš zadať nanovo.
- **Automatizácia**: Keďže reštart je automatický, uisti sa, že health checky ktoréhokoľvek reverzného proxy počítajú s krátkym reštartovacím oknom (~5 s) po obnovení.

Zálohy **neobsahujú** Redis dataset; ten len cachuje dáta, ktoré DockFlare vie znovu vypočítať. Kritickou časťou na zabezpečenie a zálohovanie je volume `/app/data` spolu s archívom.
