# Korzystanie z domen wieloznacznych

DockFlare obsługuje używanie domen z symbolami wieloznacznymi (np. `*.example.com`) do kierowania ruchu z wielu subdomen do jednej usługi. Jest to szczególnie przydatne w przypadku aplikacji obsługujących dynamiczne subdomeny, takich jak usługi dla wielu dzierżawców lub osobiste pulpity nawigacyjne, takie jak Heimdall.

## Jak to działa

Jeśli użyjesz nazwy hosta z symbolem wieloznacznym, tunel Cloudflare przekieruje cały ruch z dowolnej subdomeny, która nie ma bardziej szczegółowego rekordu DNS, do określonej usługi.

Na przykład, jeśli skonfigurujesz `*.apps.example.com`, ruch dla `service1.apps.example.com`, `service2.apps.example.com` itd. będzie kierowany do tego samego kontenera docelowego.

## Ważne uwagi

W przeciwieństwie do zwykłych nazw hostów, DockFlare **nie może automatycznie tworzyć rekordów DNS dla domen z symbolami wieloznacznymi**. Musisz ręcznie utworzyć rekord DNS z symbolem wieloznacznym w panelu kontrolnym Cloudflare.

DockFlare nadal będzie zarządzać **regułą ingress** w Cloudflare Tunnel, ale początkowa konfiguracja DNS jest czynnością ręczną.

## Przewodnik krok po kroku

Oto jak poprawnie skonfigurować domenę z symbolami wieloznacznymi w DockFlare, używając jako przykładu `*.plex.example.com`.

### Krok 1: Ręcznie utwórz rekord DNS z symbolami wieloznacznymi

1. Zaloguj się do swojego **panelu Cloudflare**.
2. Przejdź do ustawień DNS swojej domeny.
3. Kliknij **Dodaj rekord** i utwórz rekord CNAME z następującymi szczegółami:
    * **Typ:** `CNAME`
    * **Nazwa:** `*.plex` (lub po prostu `*`, jeśli Twoja główna domena to `plex.example.com`)
    * **Cel:** publiczna nazwa hosta Twojego tunelu. Znajdziesz to na pulpicie nawigacyjnym Cloudflare Zero Trust w sekcji **Access -> Tunnels**. Będzie wyglądać mniej więcej tak: `your-tunnel-uuid.cfargotunnel.com`.
    * **Status proxy:** Upewnij się, że jest to **Proxied** (pomarańczowa chmura).

    Ten ręczny rekord DNS mówi Cloudflare, aby wysłał cały ruch dla `*.plex.example.com` do Twojego tunelu.

### Krok 2: Skonfiguruj usługę za pomocą etykiety wieloznacznej

Teraz skonfiguruj swoją usługę w pliku `docker-compose.yml` z etykietą nazwy hosta z symbolem wieloznacznym.

```yaml
services:
  my-proxy-manager:
    image: nginxproxymanager/nginx-proxy-manager
    restart: unless-stopped
    networks:
      - cloudflare-net
    labels:
      - "dockflare.enable=true"
      # Tutaj użyj nazwy hosta z wildcardem
      - "dockflare.hostname=*.plex.example.com"
      - "dockflare.service=http://my-proxy-manager:81"
```

### Krok 3: Wdróż i zweryfikuj

1. Zapisz plik `docker-compose.yml` i uruchom `docker compose up -d`.
2. DockFlare wykryje kontener i utworzy regułę ingress w Cloudflare Tunnel dla nazwy hosta `*.plex.example.com`.
3. Możesz to sprawdzić w panelu administracyjnym DockFlare oraz w konfiguracji tunelu w panelu Cloudflare.

Teraz każde żądanie kierowane do subdomeny, takiej jak `sonarr.plex.example.com` lub `radarr.plex.example.com`, będzie kierowane przez tunel Cloudflare do kontenera `my-proxy-manager`, który następnie będzie mógł odpowiednio obsłużyć ruch.
