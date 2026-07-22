# Rýchly štart (Docker Compose)

Táto príručka prevádza najrýchlejším spôsobom, ako spustiť DockFlare so spevneným socket proxy a rootless konfiguráciou Mastera.

## Možnosť A — Jednoriadková inštalácia (odporúčané)

Najrýchlejší spôsob, ako rozbehnúť DockFlare, je interaktívny inštalačný skript hostovaný na [dockflare.app](https://dockflare.app):

```bash
bash <(curl -fsSL https://dockflare.app/install.sh)
```

Skript ťa prevedie:
1. Výberom inštalačného adresára (predvolene: `~/dockflare/`).
2. Výberom lokálneho UI portu (predvolene: `5000`).
3. Voliteľným nakonfigurovaním Cloudflare tunela pre samotný DockFlare.
4. Voliteľným zapnutím e-mailového profilu (dockflare-mail-manager + dockflare-webmail).

Potom zapíše `docker-compose.yml`, umožní ti ho skontrolovať a spýta sa pred stiahnutím a spustením stacku.

Keď beží, otvor `http://<ip-tvojho-servera>:5000` a dokonči sprievodcu nastavením.

---

## Možnosť B — Manuálny Docker Compose

Ak si radšej spravuješ compose súbor sám, riaď sa krokmi nižšie.

### 1. Vytvor súbor `docker-compose.yml`

Stack nižšie spúšťa docker-socket-proxy, pripraví trvalý volume so správnym vlastníctvom a spustí DockFlare popri Redise.

```yaml
services:
  docker-socket-proxy:
    image: tecnativa/docker-socket-proxy:v0.4.1
    container_name: docker-socket-proxy
    restart: unless-stopped
    logging:
      driver: "none"
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
    command: ["sh", "-c", "chown -R ${DOCKFLARE_UID:-65532}:${DOCKFLARE_GID:-65532} /app/data"]
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
      - "5000:5000" # Voliteľné: zakomentuj po vystavení cez Cloudflare Tunnel s Access politikou, aby si prístup obmedzil len na tunel
    #labels: # -- Konfigurácia Cloudflare Tunnel (cez DockFlare) VOLITEĽNÉ --
      # Hlavný DockFlare s prístupovou politikou
      #- dockflare.enable=true
      #- dockflare.hostname=dockflare.TLD  # nahraď svojou doménou
      #- dockflare.service=http://dockflare:5000
      #- dockflare.access.group=YOUR-ACCESS-GROUP-ID  # tvoja vlastná prístupová politika
      # -- OAuth callback cesta (bypass Access politika) VOLITEĽNÉ --
      # Potrebné, ak používaš OAuth overovanie s prístupovými politikami na hlavnom rozhraní
      #- dockflare.0.hostname=dockflare.example.tld
      #- dockflare.0.path=/auth/google/callback
      #- dockflare.0.service=http://dockflare:5000
      #- dockflare.0.access.group=public-default-bypass

      # V prípade potreby pridaj ďalšie callback cesty pre iných OAuth providerov
      # - dockflare.1.hostname=dockflare.example.com
      # - dockflare.1.path=/auth/github/callback
      # - dockflare.1.service=http://dockflare:5000
      # - dockflare.1.access.group=public-default-bypass
    volumes:
      - dockflare_data:/app/data
    environment:
      - REDIS_URL=redis://redis:6379/0
      - REDIS_DB_INDEX=0
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

  redis:
    image: redis:7-alpine
    container_name: dockflare-redis
    restart: unless-stopped
    command: ["redis-server", "--save", "", "--appendonly", "no"]
    logging:
      driver: "none"
    volumes:
      - dockflare_redis:/data
    networks:
      - dockflare-internal

  dockflare-mail-manager:
    image: alplat/dockflare-mail-manager:stable
    container_name: dockflare-mail-manager
    restart: unless-stopped
    profiles: ["email"]
    environment:
      - DOCKFLARE_MASTER_URL=http://dockflare:5000
      - MAIL_DATA_PATH=/data
    volumes:
      - mail_data:/data
    depends_on:
      dockflare:
        condition: service_started
    networks:
      - cloudflare-net
      - dockflare-internal

  dockflare-webmail:
    image: alplat/dockflare-webmail:stable
    container_name: dockflare-webmail
    restart: unless-stopped
    profiles: ["email"]
    environment:
      - DOCKFLARE_MASTER_URL=https://dockflare.TLD  # nahraď svojou doménou
    labels:
      - dockflare.enable=true
      - dockflare.hostname=mail.dockflare.TLD  # nahraď svojou doménou
      - dockflare.service=http://dockflare-webmail:80
    depends_on:
      dockflare-mail-manager:
        condition: service_started
    networks:
      - cloudflare-net
      - dockflare-internal

volumes:
  dockflare_data:
  dockflare_redis:
  mail_data:

networks:
  cloudflare-net:
    name: cloudflare-net
    external: true
  dockflare-internal:
    name: dockflare-internal
```

**Poznámky:**
- Kontajner Mastera beží ako používateľ `dockflare` (UID/GID 65532). Ak potrebuješ zosúladiť iné oprávnenia hostiteľa, nastav `DOCKFLARE_UID`/`DOCKFLARE_GID` a prestav image alebo uprav init úlohu.
- Proxy je povinné. DockFlare nikdy nepripája `/var/run/docker.sock` priamo, čo obmedzuje plochu Docker API, ku ktorej Master dosiahne.
- Pri použití bind mountov namiesto pomenovaných volumes zabezpeč, aby bol cieľový adresár zapisovateľný pre UID/GID 65532 (alebo tvoje prepísané hodnoty).
- Externú sieť vytvor raz, ak neexistuje: `docker network create cloudflare-net`.

### 2. Vytvor externú sieť

Ak ešte neexistuje:

```bash
docker network create cloudflare-net
```

### 3. Spusti DockFlare

Spusti stack v odpojenom režime:

```bash
docker compose up -d
```

Tým sa spustí proxy, pripraví volume a naštartuje DockFlare spolu s Redisom.

### 4. Dokonči predletové nastavenie

Keď služby bežia, otvor v prehliadači `http://<ip-tvojho-servera>:5000`.

**Predletový sprievodca nastavením** ťa prevedie:
1. Vytvorením hesla pre webové rozhranie.
2. Zadaním tvojich Cloudflare prihlasovacích údajov (Account ID, Zone ID, API token).
3. Nakonfigurovaním úvodného Cloudflare tunela.
4. *(Voliteľné)* Obnovením zo zálohovacieho archívu DockFlare. Ak už máš `dockflare_backup_*.zip`, zvoľ **Obnoviť zo zálohy** pred krokom 1; sprievodca naimportuje tvoju konfiguráciu a automaticky reštartuje kontajner.

### 5. Pre existujúcich používateľov (aktualizácia)

Ak aktualizuješ zo staršieho vydania, DockFlare zistí starší `.env` súbor, migruje tvoju konfiguráciu do zašifrovaného úložiska a prevedie ťa vytvorením hesla. Ponechaj socket proxy na mieste — priame pripojenie `/var/run/docker.sock` sa už nepodporuje.
