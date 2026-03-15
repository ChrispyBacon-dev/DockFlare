# Health Checks (Gesundheitsprüfungen)

DockFlare bietet einen dedizierten Endpunkt zur Integritätsprüfung (Health Check), der mit dem integrierten Health-Check-Mechanismus von Docker verwendet werden kann. Dadurch kann Docker den Status der DockFlare-Anwendung überwachen und sie automatisch neu starten, falls sie nicht mehr reagiert.

## Der Endpunkt `/ping`

DockFlare stellt einen einfachen HTTP-Endpunkt unter `/ping` bereit.

*   **Zweck:** Einen simplen Weg für automatisierte Systeme bereitzustellen, um zu prüfen, ob der DockFlare Webserver läuft und reagiert.
*   **Authentifizierung:** Dieser Endpunkt ist **von der Authentifizierung ausgenommen**. Sie müssen nicht eingeloggt sein, um darauf zuzugreifen. Genau dies ermöglicht es dem internen Health-Check-Mechanismus von Docker, ihn zu nutzen.
*   **Gesunde Antwort:** Eine gesunde, laufende DockFlare-Anwendung antwortet auf eine Anfrage an `/ping` mit einem **HTTP 200 OK** Statuscode.
*   **Versionsinformation:** Der Response-Body (Antworttext) der `/ping`-Schnittstelle enthält ebenfalls die aktuell laufende Version der DockFlare-Anwendung.

## Wie man einen Health Check in Docker Compose konfiguriert

Sie können Ihrer `dockflare`-Service-Konfiguration in der Datei `docker-compose.yml` einen `healthcheck`-Abschnitt hinzufügen, damit Docker den Gesundheitszustand der Applikation automatisch überwacht.

```yaml
services:
  dockflare:
    image: alplat/dockflare:stable
    container_name: dockflare
    restart: unless-stopped
    # ... other settings
    healthcheck:
      # The command to run to check health.
      # curl is used to make an HTTP request to the ping endpoint.
      test: ["CMD", "curl", "-f", "http://localhost:5000/ping"]
      # How often to run the check
      interval: 1m30s
      # How long to wait for a response
      timeout: 10s
      # How many consecutive failures before marking as unhealthy
      retries: 3
      # How long to wait after the container starts before running the first check
      start_period: 40s
```

### Aufschlüsselung der `healthcheck`-Konfiguration:

*   `test`: Dies ist der Befehl, den Docker innerhalb des Containers ausführt. `curl -f` sendet eine HTTP-Anfrage an den `/ping`-Endpunkt und bricht mit einem Statuscode ungleich null ab, wenn die Antwort nicht HTTP 200 OK lautet.
*   `interval`: Docker führt diese Prüfung alle 90 Sekunden aus.
*   `timeout`: Docker wartet bis zu 10 Sekunden auf die Ausführung des Befehls.
*   `retries`: Schlägt die Prüfung 3-mal hintereinander fehl, markiert Docker den Container als `unhealthy` (ungesund).
*   `start_period`: Docker wartet nach dem Containerstart noch 40 Sekunden auf die Initialisierung der Applikation, bevor der erste Test erfolgt. Dies gibt der App genügend Zeit, um richtig hochzufahren.

Mit dieser Konfiguration können Sie die Gesundheit Ihres Containers durch den Befehl `docker ps` abfragen. Die Status-Spalte zeigt `(healthy)` an, sofern der Check erfolgreich verläuft. Wird ein Container "unhealthy", wird er von Docker gemäß der eingestellten `restart`-Policy (z.B. `unless-stopped`) automatisch neu gestartet.
