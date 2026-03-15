# Wildcard-Domains bruuche

Mit DockFlare chasch o Wildcard-Domains wie `*.example.com` bruuche, zum mehri Subdomains a dä glychi Dienst wyterzleite. Das isch bsunders nützlich für Apps mit dynamische Subdomains.

## Wie s funktioniert

Wänn du e Wildcard-Hostname definiersch, leitet dr Cloudflare-Tunnel dr Traffic vo aune passende Subdomains a dä Ziel-Dienst wyter, usser es git scho e spezifischere DNS-Iitrag.

Zum Bispil: `*.apps.example.com` deckt `service1.apps.example.com`, `service2.apps.example.com` usw. ab.

## Was wichtig isch

Im Gägesatz zu normale Hostname cha DockFlare **kei Wildcard-DNS-Iiträg automatisch aalege**. D Wildcard muesch du im Cloudflare-Dashboard sälber erstelle.

DockFlare verwaltet aber witerhin d **Ingress-Regel** im Tunnel. Nume dr DNS-Iitrag isch e manuelle Schritt.

## Schritt für Schritt

So richtsch `*.plex.example.com` korrekt ii:

### Schritt 1: Wildcard-DNS-Iitrag manuell aalege

1.  Mäld di aa in dim **Cloudflare Dashboard** an.
2.  Navigier zu den DNS-Istellige dinere Domain.
3.  Klick uf **Add record** (Eintrag hinzufügen) u erstell einen CNAME-Eintrag mit folgenden Details:
    *   **Type:** `CNAME`
    *   **Name:** `*.plex` (oder nur `*`, wenn dini Hauptdomain `plex.example.com` isch)
    *   **Target:** Der öffentliche Hostname din Tunnels. Du findscht diesen in dim Cloudflare Zero Trust Dashboard unter **Access -> Tunnels**. Er sieht in etwa aus wie `ihr-tunnel-uuid.cfargotunnel.com`.
    *   **Proxy status:** lueg dass er auf **Proxied** (orange Wolke) gesetzt isch.

    So weiss Cloudflare, dass dr ganz Traffic für `*.plex.example.com` zu dim Tunnel söll.

### Schritt 2: Dienst mit em Wildcard-Label konfiguriere

Trag nachhär i dr `docker-compose.yml` dr Wildcard-Hostname ii:

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

### Schritt 3: Deploye u prüefe

1.  Speicher dini `docker-compose.yml`-Datei u führ `docker compose up -d` aus.
2.  DockFlare erkennt dr Container u legt e Ingress-Regel für `*.plex.example.com` a.
3.  Das chasch i dr DockFlare Web UI u im Cloudflare-Dashboard kontrolliere.

Nachhär geit jedi Aafrag a `sonarr.plex.example.com`, `radarr.plex.example.com` usw. dür dr Tunnel a dim `my-proxy-manager` wyter.
