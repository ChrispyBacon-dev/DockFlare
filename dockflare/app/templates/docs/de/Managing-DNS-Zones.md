# Verwaltung von DNS-Zonen

DockFlare ist in der Lage, DNS-Einträge über mehrere Domains (Cloudflare Zones) innerhalb desselben Cloudflare-Kontos hinweg zu verwalten. Dies ermöglicht es Ihnen, Dienste sowohl auf `service-a.domain-one.com` als auch auf `service-b.another-domain.org` von derselben DockFlare-Instanz aus zu betreiben.

## Standard-Zone

Während der anfänglichen Einrichtung von DockFlare geben Sie eine **Zone ID** an. Dies ist die **Standard-Zone**, in der DockFlare alle DNS-Einträge erstellt. Wenn Sie lediglich eine einzelne Domain nutzen möchten, reicht dies vollkommen aus.

## Die Zone mit einem Label überschreiben

Um einen Dienst in einer anderen Domäne als in der konfigurierten Standard-Zone zu verwalten, können Sie das Label `dockflare.zonename` verwenden.

Dieses Label weist DockFlare an, den DNS-Eintrag für diesen bestimmten Dienst explizit in der von Ihnen benannten Cloudflare-Zone anzulegen.

### Voraussetzungen

Damit dies funktioniert, müssen Sie garantieren, dass das **Cloudflare API-Token**, welches Sie verwenden, über die Berechtigung `Zone:DNS:Edit` für **alle** von Ihnen beabsichtigten Zonen verfügt.

### Beispiel

Angenommen, Ihre Standard-Zone ist `example.com`, aber Sie möchten nun einen neuen Dienst auf `media.io` bereitstellen.

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

Wenn Sie dies ausrollen (deployen), geschieht durch DockFlare folgendes:
1.  Ein CNAME-Eintrag für `nginx.example.com` in der `example.com` Zone wird erstellt.
2.  Ein CNAME-Eintrag für `portainer.media.io` in der `media.io` Zone wird erstellt.

Beide Hostnamen werden als Ingress-Route an denselben Cloudflare Tunnel gereiht.

## Ansicht Ihrer DNS-Einträge in der Benutzeroberfläche

Auf der **Settings**-Seite zeigt DockFlare alle Cloudflare Tunnels in Ihrem Account sowie die zugehörigen CNAME-DNS-Einträge, die auf diese Tunnels verweisen.

Wenn Sie zusätzlich zur Standard-Zone auch weitere Zonen in dieser Ansicht berücksichtigen möchten, setzen Sie die Umgebungsvariable `TUNNEL_DNS_SCAN_ZONE_NAMES`.

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

Damit erhalten Sie in der Tunnel-Übersicht eine vollständige Auflistung der relevanten DNS-Einträge über alle angegebenen Zonen hinweg.
