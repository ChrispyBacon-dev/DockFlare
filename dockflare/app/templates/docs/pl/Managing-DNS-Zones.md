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
  # Ta usługa zostanie utworzona w strefie domyślnej (example.com)
  service-one:
    image: nginx
    labels:
      - "dockflare.enable=true"
      - "dockflare.hostname=nginx.example.com"
      - "dockflare.service=http://service-one:80"

  # Ta usługa zostanie utworzona w strefie „media.io”
  service-two:
    image: portainer/portainer-ce
    labels:
      - "dockflare.enable=true"
      - "dockflare.hostname=portainer.media.io"
      - "dockflare.service=http://service-two:9000"
      # Nadpisz strefę domyślną dla tej usługi
      - "dockflare.zonename=media.io"
```

Po wdrożeniu DockFlare:
1. Utwórz rekord CNAME dla `nginx.example.com` w strefie `example.com`.
2. Utwórz rekord CNAME dla `portainer.media.io` w strefie `media.io`.

Obie nazwy hostów zostaną dodane jako reguły ingress do tego samego Cloudflare Tunnel.

## Wyświetlanie rekordów DNS w panelu administracyjnym

Na stronie **Ustawienia** panelu DockFlare znajdziesz widok wszystkich Cloudflare Tunnel na Twoim koncie oraz rekordów DNS wskazujących na te tunele.

Aby mieć pewność, że panel znajdzie rekordy DNS we wszystkich strefach, możesz użyć zmiennej środowiskowej `TUNNEL_DNS_SCAN_ZONE_NAMES`.

### `TUNNEL_DNS_SCAN_ZONE_NAMES`

Ta zmienna środowiskowa przyjmuje listę nazw stref rozdzielonych przecinkami. DockFlare będzie je skanował podczas wyszukiwania rekordów DNS.

**Przykład `docker-compose.yml`:**
```yaml
services:
  dockflare:
    image: alplat/dockflare:stable
    # ... other settings
    environment:
      # Poleć panelowi skanowanie tych stref oprócz strefy domyślnej
      - TUNNEL_DNS_SCAN_ZONE_NAMES=media.io,another-domain.org
```

Dzięki temu widok rekordów DNS pokaże wszystkie domeny wskazujące na Twoje tunele.
