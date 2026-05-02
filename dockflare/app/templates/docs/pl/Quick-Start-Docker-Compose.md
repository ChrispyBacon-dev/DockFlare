# Szybki start (Docker Compose)

Ten przewodnik pokazuje najszybszy sposób uruchomienia DockFlare z wzmocnionym `docker-socket-proxy` oraz konfiguracją Master w trybie rootless.

## Opcja A — Instalacja jednym poleceniem (Zalecane)

Najszybszym sposobem uruchomienia DockFlare jest interaktywny skrypt instalacyjny dostępny na [dockflare.app](https://dockflare.app):

```bash
bash <(curl -fsSL https://dockflare.app/install.sh)
```

Skrypt przeprowadzi Cię przez:
1. Wybór katalogu instalacji (domyślnie: `~/dockflare/`).
2. Wybór lokalnego portu interfejsu (domyślnie: `5000`).
3. Opcjonalną konfigurację tunelu Cloudflare dla DockFlare.
4. Opcjonalne włączenie profilu e-mail (dockflare-mail-manager + dockflare-webmail).

Następnie generuje plik `docker-compose.yml`, umożliwia jego przegląd i pyta o potwierdzenie przed uruchomieniem stacka.

Po uruchomieniu otwórz `http://<your-server-ip>:5000` i ukończ kreator konfiguracji.

---

## Opcja B — Ręczna konfiguracja Docker Compose

### 1. Utwórz plik `docker-compose.yml`

Poniższy stos uruchamia `docker-socket-proxy`, ustawia poprawne uprawnienia dla wolumenu danych i uruchamia DockFlare razem z Redis.

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
      - "5000:5000" # Optional: comment out once exposed via Cloudflare Tunnel with an Access Policy to restrict access to tunnel-only
    #labels: # -- Cloudflare Tunnel Configuration (via DockFlare) OPTIONAL --
      # Main DockFlare with access policy
      #- dockflare.enable=true
      #- dockflare.hostname=dockflare.TLD  # replace with your domain
      #- dockflare.service=http://dockflare:5000
      #- dockflare.access.group=YOUR-ACCESS-GROUP-ID  # your custom access policy
      # -- OAuth Callback Path (Bypass Access Policy) OPTIONAL --
      # Required if using OAuth authentication with access policies on main interface
      #- dockflare.0.hostname=dockflare.example.tld
      #- dockflare.0.path=/auth/google/callback
      #- dockflare.0.service=http://dockflare:5000
      #- dockflare.0.access.group=public-default-bypass

      # Add additional callback paths for other OAuth providers as needed
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
      - DOCKFLARE_MASTER_URL=https://dockflare.TLD  # replace with your domain
    labels:
      - dockflare.enable=true
      - dockflare.hostname=mail.dockflare.TLD  # replace with your domain
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

**Uwagi:**
- Kontener główny działa jako użytkownik `dockflare` (UID/GID 65532). Jeśli chcesz dopasować różne uprawnienia hosta, ustaw `DOCKFLARE_UID`/`DOCKFLARE_GID` i odbuduj obraz lub dostosuj zadanie init.
- Proxy jest wymagane. DockFlare nigdy nie montuje bezpośrednio `/var/run/docker.sock`, co ogranicza powierzchnię Docker API, do której może dotrzeć Master.
- Używając montowania powiązań zamiast nazwanych woluminów, upewnij się, że katalog docelowy umożliwia zapis za pomocą UID/GID 65532 (lub zastąpionych wartości).
- Utwórz raz sieć zewnętrzną, jeśli nie istnieje: `docker network create cloudflare-net`.

### 2. Utwórz sieć zewnętrzną

Jeśli jeszcze nie istnieje:

```bash
docker network create cloudflare-net
```

### 3. Uruchom DockFlare

Uruchom stos w trybie odłączonym:

```bash
docker compose up -d
```

Spowoduje to uruchomienie proxy, przygotowanie wolumenów i start DockFlare razem z Redis.

### 4. Dokończ konfigurację wstępną (Pre-Flight)

Po uruchomieniu usług otwórz przeglądarkę na `http://<your-server-ip>:5000`.

**Kreator Pre-Flight** przeprowadzi Cię przez:
1. Ustawienie hasła do panelu administracyjnego.
2. Wprowadź dane uwierzytelniające Cloudflare (identyfikator konta, identyfikator strefy, token API).
3. Konfigurowanie początkowego tunelu Cloudflare.
4. *(Opcjonalnie)* Przywracanie z archiwum kopii zapasowych DockFlare. Jeśli masz już `dockflare_backup_*.zip`, wybierz **Przywróć z kopii zapasowej** przed Krokiem 1; kreator zaimportuje konfigurację i automatycznie zrestartuje kontener.

### 5. Dla istniejących użytkowników (aktualizacja)

Jeśli aktualizujesz starszą wersję, DockFlare wykryje poprzedni plik `.env`, przeniesie konfigurację do zaszyfrowanego magazynu i przeprowadzi Cię przez proces tworzenia hasła. `docker-socket-proxy` jest nadal wymagany; bezpośrednie montowanie `/var/run/docker.sock` nie jest już obsługiwane.
