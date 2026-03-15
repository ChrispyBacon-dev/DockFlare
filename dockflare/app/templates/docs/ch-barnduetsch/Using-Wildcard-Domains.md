# Verwendung von Wildcard-Domains

DockFlare unterstützt die Verwendung von Wildcard-Domains (z.B. `*.example.com`), um den Datenverkehr für mehrere Subdomains an einen einzigen Dienst weiterzuleiten. Das isch besonders nützlich für Anwendungen, die dynamische Subdomains verarbeiten, wie mandantenfähige Dienste oder persönliche Dashboards wie Heimdall.

## Wie es funktioniert

Wänn du einen Wildcard-Hostnamen bruuche, leitet der Cloudflare Tunnel jeglichen Datenverkehr für jede Subdomain, die kei spezifischeren DNS-Eintrag hat, an den von dir angegebenen Dienst weiter.

Wänn du beispielsweise `*.apps.example.com` konfigurieren, wird der Traffic für `service1.apps.example.com`, `service2.apps.example.com` u so weiter vollständig an denselben Zielcontainer geleitet.

## Wichtige Überlegungen

Im Gegensatz zu normalen Hostnamen **cha DockFlare nid automatisch DNS-Einträge für Wildcard-Domains erstellen**. Du muesch den Wildcard-DNS-Eintrag manuell in dim Cloudflare-Dashboard anlegen.

DockFlare wird weiterhin die **Ingress-Regel** in dim Cloudflare-Tunnel verwalten, aber die anfängliche DNS-Einrichtung isch ein manueller Schritt.

## Schritt-für-Schritt-Aaleitig

Hier isch, wie du eine Wildcard-Domain mit DockFlare korrekt einrichten, am Beispiel von `*.plex.example.com`.

### Schritt 1: Den Wildcard-DNS-Eintrag manuell erstellen

1.  Mäld di aa in dim **Cloudflare Dashboard** an.
2.  Navigier zu den DNS-Istellige dinere Domain.
3.  Klick auf **Add record** (Eintrag hinzufügen) u erstell einen CNAME-Eintrag mit folgenden Details:
    *   **Type:** `CNAME`
    *   **Name:** `*.plex` (oder nur `*`, wenn dini Hauptdomain `plex.example.com` isch)
    *   **Target:** Der öffentliche Hostname din Tunnels. Du findscht diesen in dim Cloudflare Zero Trust Dashboard unter **Access -> Tunnels**. Er sieht in etwa aus wie `ihr-tunnel-uuid.cfargotunnel.com`.
    *   **Proxy status:** lueg dass er auf **Proxied** (orange Wolke) gesetzt isch.

    Dieser manuelle DNS-Eintrag teilt Cloudflare mit, den gesamten Traffic für `*.plex.example.com` an dini Tunnel zu senden.

### Schritt 2: dini Dienst mit einem Wildcard-Label konfigurieren

Konfigurier nun dini Dienst in dinere `docker-compose.yml`-Datei mit einem Wildcard-Hostnamen-Label.

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

### Schritt 3: Bereitstellen u Überprüfen

1.  Speicher dini `docker-compose.yml`-Datei u führ `docker compose up -d` aus.
2.  DockFlare wird den Container erkennen u eine Ingress-Regel für den Hostnamen `*.plex.example.com` in dim Cloudflare Tunnel anlegen.
3. Du chasch dies in der DockFlare Web UI sowie in der Konfiguration din Tunnels im Cloudflare-Dashboard überprüfen.

Nun wird jede Anfrage an eine Subdomain wie `sonarr.plex.example.com` oder `radarr.plex.example.com` durch dini Cloudflare Tunnel an dini `my-proxy-manager`-Container weitergeleitet, der den Traffic dann entsprechend bearbeiten cha.
