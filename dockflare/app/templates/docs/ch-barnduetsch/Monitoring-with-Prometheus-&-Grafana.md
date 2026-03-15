# Monitoring mit Prometheus & Grafana

Dr vo DockFlare verwaltete `cloudflared`-Agent cha e ganzi Reihe Metrike im Prometheus-Format usgäh. Wänn du die sammelsch u visualisierisch, gsehsch meh über Traffic, Latenz u Fehlerrate vo dine Tunnel.

I däre Aaleitig gsehsch, wie du dr Metrik-Endpunkt aktiviersch u schnell e Monitoring-Stack mit Prometheus u Grafana iirichtsch.

## Schritt 1: Metrik-Endpunkt i DockFlare aktiviere

Zerscht seisch DockFlare, dass dr Prometheus-Metrik-Endpunkt im verwaltete `cloudflared`-Agent söll aktiviert wärde.

Das machsch über d Umgebigsvariable `CLOUDFLARED_METRICS_PORT`.

**Beispiel `docker-compose.yml`:**
```yaml
services:
  dockflare:
    image: alplat/dockflare:stable
    # ... other settings
    environment:
      # Enable the metrics endpoint on port 2000 inside the container
      - CLOUDFLARED_METRICS_PORT=2000
```
Wänn du DockFlare nachhär neu startisch, wird dr verwaltete `cloudflared`-Agent neu erstellt u dr Metrik-Server uf em aagäh Port aktiviert.

**Hinwys:** Das funktioniert nume im standardmässige **Interne Modus**. Im [Externe Modus](External-cloudflared-Mode.md) muesch du dä Endpunkt i dim eigete `cloudflared` sälber aktiviere.

## Schritt 2: Monitoring-Stack iirichte

Wänn du no kei Monitoring-Stack hesch, chasch mit Docker Compose schnäll eine iirichte. Im DockFlare-Repo git s es Bispil im Verzeichnis `/examples`.

Für e vollständigi Copy-Paste-Aaleitig lueg i d Datei **[`grafana quick setup.md`](https://github.com/ChrispyBacon-dev/DockFlare/blob/main/examples/grafana%20quick%20setup.md)** im Repo.

Die Aaleitig zeigt dir:
1. wie du d nötigi Verzeichnisstruktur aaleisch
2. wie du Prometheus u Grafana i dini `docker-compose.yml` iibausch
3. wie Prometheus d Metrike vom `cloudflared`-Agent abholt
4. wie Grafana mit dr passende Datenquelle parat gmacht wird

## Schritt 3: S fertige Grafana-Dashboard importiere

Damit s Visualisiere eifach geit, git s im Repo es fertigs Grafana-Dashboard, wo uf d Metrike vom `cloudflared`-Agent abgestimmt isch.

1.  Das Dashboard isch als **[`dashboard.json`](https://github.com/ChrispyBacon-dev/DockFlare/blob/main/examples/dashboard.json)** im Verzeichnis `/examples` des Repositorys verfügbar.
2.  Lad diese Datei herunter.
3.  Mäld di aa an dinere Grafana-Instanz an.
4.  Gang zum Bereich "Dashboards" u klick uf "Import" (Importieren).
5.  Lad die Datei `dashboard.json` hoch.
6.  Wähl dini Prometheus-Datenquelle aus u importier das Dashboard.

Nachhär hesch e guete Überblick über d Leistig vo dine Cloudflare-Tunnel, inklusive Aafrage, Fehlerrate u Verbindigslatenz.

![Grafana Dashboard Beispiel](../static/images/grafana_dashboard_example.png)
