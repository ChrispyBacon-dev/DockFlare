# Health Checks

DockFlare het e eigete Endpunkt für Health Checks. Dä chasch mit em Docker-Healthcheck verknüpfe, damit Docker überwacht, öb d Aawändig no sauber reagiert, u dr Container automatisch neu startet, falls öppis hängt.

## Der Endpunkt `/ping`

DockFlare stellt eifach dr HTTP-Endpunkt `/ping` bereit.

* **Zweck:** Automatisiert prüefe, öb dr DockFlare-Webserver lauft u antwortet.
* **Authentifizierig:** Uf `/ping` chasch ohni Login zugryfe. Genau drum cha Docker dä Check intern bruuche.
* **Gsuendi Antwort:** E laufendi Instanz git uf `/ping` es **HTTP 200 OK** zrügg.
* **Versionsinfo:** Im Antworttext steit o d aktuell lauffendi DockFlare-Version.

## So richtsch dr Health Check i Docker Compose i

Füeg i dinere `docker-compose.yml` bim `dockflare`-Service e `healthcheck`-Abschnitt ii, damit Docker d Aawändig automatisch überwacht.

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

### Was d `healthcheck`-Wärt bedüte

* `test`: Dr Befehl, wo Docker im Container usfüehrt. `curl -f` prüeft, öb `/ping` e gültigi Antwort git.
* `interval`: Docker macht dä Check alli 90 Sekunde.
* `timeout`: So lang wartet Docker höchstens uf e Antwort.
* `retries`: Nach dr dritte fehlgschlagene Prüefig gilt dr Container als `unhealthy`.
* `start_period`: Git dr App nach em Start no chli Zyt, bevor dr erscht Check lauft.

Mit däre Konfiguration gsehsch bi `docker ps`, öb dr Container `(healthy)` isch. Wänn er `unhealthy` wird, startet Docker ihn je nach `restart`-Policy automatisch neu.
