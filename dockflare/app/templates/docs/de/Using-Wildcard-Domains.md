# Verwendung von Wildcard-Domains

DockFlare unterstützt die Verwendung von Wildcard-Domains (z.B. `*.example.com`), um den Datenverkehr für mehrere Subdomains an einen einzigen Dienst weiterzuleiten. Dies ist besonders nützlich für Anwendungen, die dynamische Subdomains verarbeiten, wie mandantenfähige Dienste oder persönliche Dashboards wie Heimdall.

## Wie es funktioniert

Wenn Sie einen Wildcard-Hostnamen verwenden, leitet der Cloudflare Tunnel jeglichen Datenverkehr für jede Subdomain, die keinen spezifischeren DNS-Eintrag hat, an den von Ihnen angegebenen Dienst weiter.

Wenn Sie beispielsweise `*.apps.example.com` konfigurieren, wird der Traffic für `service1.apps.example.com`, `service2.apps.example.com` und so weiter vollständig an denselben Zielcontainer geleitet.

## Wichtige Überlegungen

Im Gegensatz zu normalen Hostnamen **kann DockFlare nicht automatisch DNS-Einträge für Wildcard-Domains erstellen**. Sie müssen den Wildcard-DNS-Eintrag manuell in Ihrem Cloudflare-Dashboard anlegen.

DockFlare wird weiterhin die **Ingress-Regel** in Ihrem Cloudflare-Tunnel verwalten, aber die anfängliche DNS-Einrichtung ist ein manueller Schritt.

## Schritt-für-Schritt-Anleitung

Hier ist, wie Sie eine Wildcard-Domain mit DockFlare korrekt einrichten, am Beispiel von `*.plex.example.com`.

### Schritt 1: Den Wildcard-DNS-Eintrag manuell erstellen

1.  Melden Sie sich in Ihrem **Cloudflare Dashboard** an.
2.  Navigieren Sie zu den DNS-Einstellungen Ihrer Domain.
3.  Klicken Sie auf **Add record** (Eintrag hinzufügen) und erstellen Sie einen CNAME-Eintrag mit folgenden Details:
    *   **Type:** `CNAME`
    *   **Name:** `*.plex` (oder nur `*`, wenn Ihre Hauptdomain `plex.example.com` ist)
    *   **Target:** Der öffentliche Hostname Ihres Tunnels. Sie finden diesen in Ihrem Cloudflare Zero Trust Dashboard unter **Access -> Tunnels**. Er sieht in etwa aus wie `ihr-tunnel-uuid.cfargotunnel.com`.
    *   **Proxy status:** Stellen Sie sicher, dass er auf **Proxied** (orange Wolke) gesetzt ist.

    Dieser manuelle DNS-Eintrag teilt Cloudflare mit, den gesamten Traffic für `*.plex.example.com` an Ihren Tunnel zu senden.

### Schritt 2: Ihren Dienst mit einem Wildcard-Label konfigurieren

Konfigurieren Sie nun Ihren Dienst in Ihrer `docker-compose.yml`-Datei mit einem Wildcard-Hostnamen-Label.

```yaml
services:
  my-proxy-manager:
    image: nginxproxymanager/nginx-proxy-manager
    restart: unless-stopped
    networks:
      - cloudflare-net
    labels:
      - "dockflare.enable=true"
      # Use the wildcard hostname here
      - "dockflare.hostname=*.plex.example.com"
      - "dockflare.service=http://my-proxy-manager:81"
```

### Schritt 3: Bereitstellen und Überprüfen

1.  Speichern Sie Ihre `docker-compose.yml`-Datei und führen Sie `docker compose up -d` aus.
2.  DockFlare wird den Container erkennen und eine Ingress-Regel für den Hostnamen `*.plex.example.com` in Ihrem Cloudflare Tunnel anlegen.
3.  Sie können dies in der DockFlare Web-UI sowie in der Konfiguration Ihres Tunnels im Cloudflare-Dashboard überprüfen.

Nun wird jede Anfrage an eine Subdomain wie `sonarr.plex.example.com` oder `radarr.plex.example.com` durch Ihren Cloudflare Tunnel an Ihren `my-proxy-manager`-Container weitergeleitet, der den Traffic dann entsprechend bearbeiten kann.
