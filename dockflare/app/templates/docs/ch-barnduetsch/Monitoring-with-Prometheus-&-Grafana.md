# Überwachung mit Prometheus & Grafana

Der von DockFlare verwaltete `cloudflared`-Agent cha eine Vielzahl von Leistungs- u Integritätsmetriken im Prometheus-Format bereitstelle. Durch das Sammeln u Visualisieren dieser Metriken chasch wertvolle Einblicke in den Datenverkehr, die Latenz u die Fehlerraten din Tunnels gewinnen.

Diese Aaleitig erklärt, wie du den Metrik-Endpunkt aktivieren u bietet eine schnelle Einrichtung für einen Monitoring-Stack mit Prometheus u Grafana.

## Schritt 1: Aktivieren des Metrik-Endpunkts in DockFlare

Der erste Schritt besteht darin, DockFlare anzuweisen, den Prometheus-Metrik-Endpunkt in seinem verwalteten `cloudflared`-Agenten zu aktivieren.

Du chasch dies tun, indem du die Umgebungsvariable `CLOUDFLARED_METRICS_PORT` für dini DockFlare-Container setzen.

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
Wänn du DockFlare mit dieser Variablen neu starten, wird der verwaltete `cloudflared`-Agent automatisch mit dem auf dem angegebenen Port aktivierten Metrik-Server neu erstellt.

**Hinweis:** Diese Funktion isch nur im standardmässigen **Internen Modus** verfügbar. Wänn du den [Externen Modus](External-cloudflared-Mode.md) bruuche, si du selbst dafür verantwortlich, den Metrik-Endpunkt in dim eigenen `cloudflared`-Agenten zu aktivieren.

## Schritt 2: Einrichten eines Monitoring-Stacks

Wänn du no kei Monitoring-Stack hesch, chasch mit Docker Compose schnell eine iirichte. S'DockFlare-Repo het es Biispil-Setup im Verzeichnis `/examples`.

Für eine vollständige Aaleitig zum Kopieren u Einfügen zur Einrichtung von Prometheus u Grafana zur Überwachung von DockFlare läs bitte die Datei **[`grafana quick setup.md`](https://github.com/ChrispyBacon-dev/DockFlare/blob/main/examples/grafana%20quick%20setup.md)** im Repository.

Diese Aaleitig führt du durch:
1.  Die Erstellung der notwendigen Verzeichnisstruktur.
2.  Das Hinzufügen der Prometheus- u Grafana-Dienste zu dinere `docker-compose.yml`.
3.  Die Konfiguration von Prometheus zum Abrufen von Metriken aus dem `cloudflared`-Agenten.
4.  Die automatische Bereitstellige von Grafana mit der Prometheus-Datenquelle.

## Schritt 3: Importieren des vorgefertigten Grafana-Dashboards

Um die Visualisierung einfach zu machen, bietet DockFlare ein vorgefertigtes Grafana-Dashboard, das perfekt auf die vom `cloudflared`-Agenten bereitgestellten Metriken abgestimmt isch.

1.  Das Dashboard isch als **[`dashboard.json`](https://github.com/ChrispyBacon-dev/DockFlare/blob/main/examples/dashboard.json)** im Verzeichnis `/examples` des Repositorys verfügbar.
2.  Lad diese Datei herunter.
3.  Mäld di aa an dinere Grafana-Instanz an.
4.  Gang zum Bereich "Dashboards" u klick uf "Import" (Importieren).
5.  Lad die Datei `dashboard.json` hoch.
6.  Wähl dini Prometheus-Datenquelle aus u importier das Dashboard.

Du hesch nun einen vollständigen Überblick über die Leistung din Cloudflare-Tunnels, einschliesslich Anfragezahlen, Fehlerraten, Verbindungslatenz u mehr.

![Grafana Dashboard Beispiel](../static/images/grafana_dashboard_example.png)
