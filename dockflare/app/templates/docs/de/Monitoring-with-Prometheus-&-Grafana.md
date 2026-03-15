# Überwachung mit Prometheus & Grafana

Der von DockFlare verwaltete `cloudflared`-Agent kann eine Vielzahl von Leistungs- und Integritätsmetriken im Prometheus-Format bereitstellen. Durch das Sammeln und Visualisieren dieser Metriken können Sie wertvolle Einblicke in den Datenverkehr, die Latenz und die Fehlerraten Ihres Tunnels gewinnen.

Diese Anleitung erklärt, wie Sie den Metrik-Endpunkt aktivieren und bietet eine schnelle Einrichtung für einen Monitoring-Stack mit Prometheus und Grafana.

## Schritt 1: Aktivieren des Metrik-Endpunkts in DockFlare

Der erste Schritt besteht darin, DockFlare anzuweisen, den Prometheus-Metrik-Endpunkt in seinem verwalteten `cloudflared`-Agenten zu aktivieren.

Sie können dies tun, indem Sie die Umgebungsvariable `CLOUDFLARED_METRICS_PORT` für Ihren DockFlare-Container setzen.

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
Wenn Sie DockFlare mit dieser Variablen neu starten, wird der verwaltete `cloudflared`-Agent automatisch mit dem auf dem angegebenen Port aktivierten Metrik-Server neu erstellt.

**Hinweis:** Diese Funktion ist nur im standardmäßigen **Internen Modus** verfügbar. Wenn Sie den [Externen Modus](External-cloudflared-Mode.md) verwenden, sind Sie selbst dafür verantwortlich, den Metrik-Endpunkt in Ihrem eigenen `cloudflared`-Agenten zu aktivieren.

## Schritt 2: Einrichten eines Monitoring-Stacks

Wenn Sie noch keinen Monitoring-Stack haben, können Sie mit Docker Compose schnell einen einrichten. Das DockFlare-Repository bietet ein Beispiel-Setup im Verzeichnis `/examples`.

Für eine vollständige Anleitung zum Kopieren und Einfügen zur Einrichtung von Prometheus und Grafana zur Überwachung von DockFlare lesen Sie bitte die Datei **[`grafana quick setup.md`](https://github.com/ChrispyBacon-dev/DockFlare/blob/main/examples/grafana%20quick%20setup.md)** im Repository.

Diese Anleitung führt Sie durch:
1.  Die Erstellung der notwendigen Verzeichnisstruktur.
2.  Das Hinzufügen der Prometheus- und Grafana-Dienste zu Ihrer `docker-compose.yml`.
3.  Die Konfiguration von Prometheus zum Abrufen von Metriken aus dem `cloudflared`-Agenten.
4.  Die automatische Bereitstellung von Grafana mit der Prometheus-Datenquelle.

## Schritt 3: Importieren des vorgefertigten Grafana-Dashboards

Um die Visualisierung einfach zu machen, bietet DockFlare ein vorgefertigtes Grafana-Dashboard, das perfekt auf die vom `cloudflared`-Agenten bereitgestellten Metriken abgestimmt ist.

1.  Das Dashboard ist als **[`dashboard.json`](https://github.com/ChrispyBacon-dev/DockFlare/blob/main/examples/dashboard.json)** im Verzeichnis `/examples` des Repositorys verfügbar.
2.  Laden Sie diese Datei herunter.
3.  Melden Sie sich an Ihrer Grafana-Instanz an.
4.  Gehen Sie zum Bereich "Dashboards" und klicken Sie auf "Import" (Importieren).
5.  Laden Sie die Datei `dashboard.json` hoch.
6.  Wählen Sie Ihre Prometheus-Datenquelle aus und importieren Sie das Dashboard.

Sie haben nun einen vollständigen Überblick über die Leistung Ihres Cloudflare-Tunnels, einschließlich Anfragezahlen, Fehlerraten, Verbindungslatenz und mehr.

![Grafana Dashboard Beispiel](../static/images/grafana_dashboard_example.png)
