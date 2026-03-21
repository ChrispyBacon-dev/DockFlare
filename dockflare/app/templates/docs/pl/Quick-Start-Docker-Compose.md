# Szybki start (Docker Compose)

Ten przewodnik pokazuje najszybszy sposób uruchomienia DockFlare z wzmocnionym `docker-socket-proxy` oraz konfiguracją Master w trybie rootless.

## Opcja A — Instalacja jednym poleceniem (Zalecane)

Najszybszym sposobem uruchomienia DockFlare jest skrypt instalacyjny dostępny na [dockflare.app](https://dockflare.app):

```bash
curl -fsSL https://dockflare.app/install.sh | bash
```

Skrypt wykona następujące czynności:
1. Sprawdzi, czy Docker i Docker Compose są dostępne.
2. Utworzy katalog `~/dockflare/` i zapisze tam plik `docker-compose.yml`.
3. Utworzy sieć Docker `cloudflare-net`, jeśli jeszcze nie istnieje.
4. Pobierze obrazy i uruchomi wszystkie usługi.
5. Wyświetli lokalny adres URL po zakończeniu.

Po uruchomieniu otwórz `http://<your-server-ip>:5000` i ukończ kreator konfiguracji.

> **Opcjonalne parametry** — ustaw zmienne środowiskowe przed uruchomieniem, aby dostosować instalację:
> ```bash
> DOCKFLARE_PORT=8080 DOCKFLARE_DIR=/opt/dockflare curl -fsSL https://dockflare.app/install.sh | bash
> ```

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
      - REDIS_DB_INDEX=0  # Optional: specify Redis database index (0-15) for isolation from other containers
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
