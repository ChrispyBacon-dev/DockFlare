# Zarządzanie strefami DNS

DockFlare może zarządzać rekordami DNS w wielu domenach (strefach Cloudflare) w ramach tego samego konta Cloudflare. Umożliwia to uruchamianie usług na `service-a.domain-one.com` i `service-b.another-domain.org` z tej samej instancji DockFlare.

## Strefa domyślna

Podczas początkowej konfiguracji DockFlare podajesz **ID strefy**. To jest **strefa domyślna**, w której DockFlare utworzy wszystkie rekordy DNS. Jeśli planujesz używać tylko jednej domeny, to wszystko, o co musisz się martwić.

## Zastępowanie strefy etykietą

Aby zarządzać usługą na innej domenie niż domyślna możesz skorzystać z etykiety `dockflare.zonename`.

Ta etykieta informuje DockFlare, aby utworzył rekord DNS dla tej konkretnej usługi w określonej strefie Cloudflare.

### Warunki wstępne

Aby to zadziałało, musisz upewnić się, że **Token API Cloudflare**, którego używasz, ma uprawnienia `Zone:DNS:Edit` dla **wszystkich stref**, którymi zamierzasz zarządzać.

### Przykład

Załóżmy, że Twoja domyślna strefa to `example.com`, ale chcesz także uruchomić usługę w `media.io`.

```yaml
services:
  # This service will be created in the default zone (example.com)
  service-one:
    image: nginx
    labels:
      - "dockflare.enable=true"
      - "dockflare.hostname=nginx.example.com"
      - "dockflare.service=http://service-one:80"

  # This service will be created in the 'media.io' zone
  service-two:
    image: portainer/portainer-ce
    labels:
      - "dockflare.enable=true"
      - "dockflare.hostname=portainer.media.io"
      - "dockflare.service=http://service-two:9000"
      # Override the default zone for this service
      - "dockflare.zonename=media.io"
```

Po wdrożeniu DockFlare:
1. Utwórz rekord CNAME dla `nginx.example.com` w strefie `example.com`.
2. Utwórz rekord CNAME dla `portainer.media.io` w strefie `media.io`.

Obie nazwy hostów zostaną dodane jako reguły ingress do tego samego Cloudflare Tunnel.

## Wyświetlanie rekordów DNS w Web UI

Web UI DockFlare zawiera na stronie **Ustawienia** widok, który umożliwia przeglądanie wszystkich Cloudflare Tunnel na Twoim koncie i wskazujących je rekordów DNS.

Aby mieć pewność, że Web UI znajdzie rekordy DNS we wszystkich strefach, możesz użyć zmiennej środowiskowej `TUNNEL_DNS_SCAN_ZONE_NAMES`.

### `TUNNEL_DNS_SCAN_ZONE_NAMES`

Ta zmienna środowiskowa akceptuje rozdzieloną przecinkami listę nazw stref, które Web UI powinien skanować podczas wyszukiwania rekordów DNS.

**Przykład `docker-compose.yml`:**
```yaml
services:
  dockflare:
    image: alplat/dockflare:stable
    # ... other settings
    environment:
      # Tell the UI to scan these zones in addition to the default one
      - TUNNEL_DNS_SCAN_ZONE_NAMES=media.io,another-domain.org
```

Dzięki temu przeglądarka rekordów DNS w interfejsie użytkownika zapewni pełny obraz wszystkich domen wskazujących Twoje tunele.
