# Verwaltung von DNS-Zonen

DockFlare isch in der Lage, DNS-Einträge über mehrere Domains (Cloudflare Zones) innerhalb desselben Cloudflare-Kontos hinweg zu verwalten. Das ermöglicht es dir, Dienste sowohl auf `service-a.domain-one.com` als auch auf `service-b.another-domain.org` von derselben DockFlare-Instanz aus zu betreiben.

## Standard-Zone

Bim erschte Iirichte vo DockFlare gisch du e **Zone ID** aa. Das isch d'**Standard-Zone**, i der DockFlare alli DNS-Iiträg erstellt. Wänn du nume e einzelni Domain bruuche wotsch, längt das völlig.

## Die Zone mit einem Label überschreiben

Um einen Dienst in einer anderen Domäne als in der konfigurierten Standard-Zone zu verwalten, chasch das Label `dockflare.zonename` bruuche.

Das Label weist DockFlare an, den DNS-Eintrag für diesen bestimmten Dienst explizit in der von dir benannten Cloudflare-Zone anzulegen.

### Voraussetzige

Damit dies funktioniert, muesch garantieren, dass das **Cloudflare API-Token**, welches du bruuche, über die Berechtigung `Zone:DNS:Edit` für **alle** von dir beabsichtigten Zonen verfügt.

### Beispiel

Näh mer aa, dini Standard-Zone isch `example.com`, aber du wotsch nun einen neuen Dienst auf `media.io` bereitstelle.

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

Wänn du dies ausrollen (deployen), geschieht durch DockFlare folgendes:
1.  Ein CNAME-Eintrag für `nginx.example.com` in der `example.com` Zone wird erstellt.
2.  Ein CNAME-Eintrag für `portainer.media.io` in der `media.io` Zone wird erstellt.

Beide Hostnamen wärde als Ingress-Route an denselben Cloudflare Tunnel gereiht.

## Ansicht dinere DNS-Iiträg i dr Web UI

Auf der **Settings**-Seite zeigt DockFlare alle Cloudflare Tunnels in dim Account sowie die zugehörigen CNAME-DNS-Einträge, die auf diese Tunnels verweisen.

Wänn du zusätzlich zur Standard-Zone auch weitere Zonen in dieser Ansicht berücksichtigen wotsch, setz die Umgebungsvariable `TUNNEL_DNS_SCAN_ZONE_NAMES`.

### `TUNNEL_DNS_SCAN_ZONE_NAMES`

Diese Umgebungsvariable erwartet eine kommagetrennte Liste der Zonennamen, die die UI zusätzlich zur Standard-Zone nach Tunnel-DNS-Records durchsuchen soll.

**Beispiel `docker-compose.yml`:**
```yaml
services:
  dockflare:
    image: alplat/dockflare:stable
    # ... other settings
    environment:
      # Tell the UI to scan these zones in addition to the default one
      - TUNNEL_DNS_SCAN_ZONE_NAMES=media.io,another-domain.org
```

So hesch du i dr Tunnel-Übersicht e vollständigi Liste vo allne relevante DNS-Iiträg über alli agäh Zonen.
