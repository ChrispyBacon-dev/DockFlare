# Podstawowe użycie (pojedyncza domena)

W tym przewodniku przedstawiono najczęstszy przypadek użycia DockFlare: udostępnienie pojedynczego kontenera Docker w Internecie pod publiczną nazwą hosta.

## Warunki wstępne

Zanim zaczniesz, upewnij się, że masz:
1. Ukończono przewodnik [Szybki start](Quick-Start-Docker-Compose.md).
2. DockFlare jest uruchomiony i połączony z Twoim kontem Cloudflare.
3. Masz usługę, którą chcesz wyeksponować (w tym przykładzie użyjemy `nginx`).

## Przykład: wystawienie kontenera NGINX

Załóżmy, że chcesz udostępnić standardowy serwer WWW NGINX pod nazwą hosta `nginx.example.com`.

### 1. Dodaj usługę do swojego `docker-compose.yml`

Zmodyfikuj plik `docker-compose.yml`, aby uwzględnić usługę `nginx`. Kluczem jest dodanie do jego konfiguracji etykiet `dockflare.*`.

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

  # Add your new service here
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
      # Optional: Apply public access with zone protection bypass
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
> **Dlaczego Redis?** DockFlare korzysta z Redis do buforowania, strumieniowania logów i komunikacji między wątkami. Uruchomienie go w prywatnej sieci `dockflare-internal` sprawia, że Redis jest dostępny tylko dla DockFlare, podczas gdy workloady pozostają odizolowane w `cloudflare-net`.


### 2. Zrozumienie etykiet

* `dockflare.enable=true`: Informuje DockFlare o zarządzaniu tym kontenerem.
* `dockflare.hostname=nginx.example.com`: To jest publiczny adres URL, pod którym będzie dostępna Twoja usługa. DockFlare utworzy rekord DNS dla tej nazwy hosta na Twoim koncie Cloudflare.
* `dockflare.service=http://nginx-webserver:80`: Informuje Cloudflare Tunnel, dokąd ma wysyłać ruch. To wewnętrzny adres kontenera NGINX. Pamiętaj, że jako nazwę hosta używamy nazwy usługi (`nginx-webserver`), co działa, bo oba kontenery są w tej samej sieci Dockera.
* `dockflare.access.group=public-default-bypass`: (Opcjonalnie) Używa zasady obejścia systemu, aby zapewnić publiczny dostęp, nawet jeśli istnieje zasada ochrony `*.example.com` na poziomie strefy. Jest to ważne, jeśli masz zasady dotyczące symboli wieloznacznych chroniących Twoją domenę, ale potrzebujesz określonych usług, aby pozostały publiczne.

### 3. Wdróż usługę

Zapisz plik `docker-compose.yml` i uruchom następujące polecenie, aby uruchomić nową usługę:

```bash
docker compose up -d
```

### 4. Weryfikacja

DockFlare wykryje nowy kontener i automatycznie wykona następujące czynności:
1. Dodaj regułę ingress do Cloudflare Tunnel dla `nginx.example.com`.
2. Utwórz rekord CNAME dla `nginx.example.com` w swoim DNS Cloudflare, wskazując tunel.

Możesz to zweryfikować na kilka sposobów:
* **Panel administracyjny DockFlare**: Usługa `nginx.example.com` pojawi się na pulpicie nawigacyjnym.
* **Cloudflare Dashboard**: Zobaczysz nowy rekord CNAME w ustawieniach DNS i nową regułę ingress w konfiguracji tunelu.

Po kilku chwilach, zanim DNS się rozpropaguje, powinieneś móc przejść do `https://nginx.example.com` w przeglądarce i zobaczyć domyślną stronę powitalną NGINX.

## Szczegóły kopii zapasowej i przywracania

DockFlare zapewnia najwyższej klasy przepływ kopii zapasowych, dzięki czemu możesz przenieść lub odzyskać instancję w ciągu kilku minut.

### Co zawiera archiwum kopii zapasowych

Kiedy pobierasz kopię zapasową z **Ustawienia → Kopia zapasowa i przywracanie** (lub kreatora dołączania), DockFlare generuje `.zip` z następującymi plikami:

| Plik | Opis |
| --- | --- |
| `dockflare_config.dat` | Zaszyfrowany pakiet konfiguracyjny (poświadczenia Cloudflare, skrót hasła do panelu administracyjnego, domyślne ustawienia tunelu, klucz API Mastera itd.). |
| `dockflare.key` | Klucz Fernet używany do odszyfrowywania `dockflare_config.dat` i innych zaszyfrowanych ładunków. Zachowaj to w archiwum. |
| `agent_keys.dat` | Zaszyfrowany rejestr kluczy API agenta, metadanych i statusu unieważnienia. |
| `state.json` | Zwykła migawka JSON stanu środowiska wykonawczego — zarządzane reguły, agenci, grupy dostępu. Jest to uwzględnione, aby operatorzy mogli w razie potrzeby sprawdzać lub migrować określone elementy. |
| `manifest.json` | Sumy kontrolne i informacje o wersji każdego pliku w archiwum. |

Kopia zapasowa jest samodzielna: przywrócenie jej za pomocą kreatora/punktu końcowego aplikacji powoduje zapisanie każdego pliku w `/app/data/` i natychmiastowe planowanie ponownego uruchomienia kontenera, tak aby zaszyfrowana konfiguracja została ponownie załadowana podczas rozruchu.

### Uwagi dotyczące przywracania i zgodności

- **Kreator i Settings UI**: Prześlij `.zip`, a DockFlare zaimportuje go, przeładuje stan i zakończy pracę. Docker automatycznie uruchomi kontener ponownie, więc wrócisz do trybu operacyjnego bez ręcznej interwencji.
- **Starsza wersja `state.json`**: w przypadku rozwiązywania problemów lub zaawansowanych przepływów pracy nadal możesz przesłać tylko plik `state.json`. DockFlare wypełni z niego stan środowiska wykonawczego, ale pominie zaszyfrowaną konfigurację; należy później ponownie wprowadzić dane uwierzytelniające.
- **Automatyzacja**: Ponieważ ponowne uruchomienie następuje automatycznie, upewnij się, że wszelkie kontrole stanu odwrotnego proxy pozwalają na krótkie okno ponownego uruchomienia (~5 s) po przywróceniu.

Kopie zapasowe **nie** obejmują zestawu danych Redis; buforuje tylko dane, które DockFlare może przeliczyć. Wolumin `/app/data` obok archiwum to kluczowy element, który należy zabezpieczyć i utworzyć kopię zapasową.
