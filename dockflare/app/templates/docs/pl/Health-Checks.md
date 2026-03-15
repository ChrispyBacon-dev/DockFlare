# Kontrole stanu zdrowia

DockFlare zawiera dedykowany punkt końcowy sprawdzania kondycji, którego można używać z wbudowanym mechanizmem sprawdzania stanu platformy Docker. Dzięki temu Docker może monitorować stan aplikacji DockFlare i automatycznie uruchamiać ją ponownie, jeśli przestanie odpowiadać.

## Punkt końcowy `/ping`

DockFlare udostępnia prosty punkt końcowy HTTP pod adresem `/ping`.

* **Cel:** Zapewnienie prostego sposobu sprawdzania przez zautomatyzowane systemy, czy serwer WWW DockFlare działa i reaguje.
* **Uwierzytelnianie:** Ten punkt końcowy jest **zwolniony z uwierzytelniania**. Nie musisz być zalogowany, aby uzyskać do niego dostęp, dzięki czemu może z niego korzystać wewnętrzny mechanizm sprawdzania stanu Dockera.
* **Zdrowa odpowiedź:** Sprawnie działająca aplikacja DockFlare odpowie na żądanie pod adresem `/ping` kodem stanu **HTTP 200 OK**.
* **Informacje o wersji:** Treść odpowiedzi z punktu końcowego `/ping` zawiera również działającą wersję aplikacji DockFlare.

## Jak skonfigurować kontrolę stanu w Docker Compose

Możesz dodać sekcję `healthcheck` do usługi `dockflare` w pliku `docker-compose.yml`, aby Docker automatycznie monitorował stan aplikacji.

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

### Podział konfiguracji `healthcheck`:

* `test`: To jest polecenie uruchamiane przez Dockera wewnątrz kontenera. `curl -f` wyśle żądanie HTTP do punktu końcowego `/ping` i zakończy działanie z niezerowym kodem stanu, jeśli odpowiedź nie będzie HTTP 200 OK.
* `interval`: Docker będzie uruchamiał tę kontrolę co 90 sekund.
* `timeout`: Docker będzie czekać do 10 sekund na wykonanie polecenia.
* `retries`: Jeśli sprawdzenie nie powiedzie się 3 razy z rzędu, Docker oznaczy kontener jako `unhealthy`.
* `start_period`: Docker odczeka 40 sekund po uruchomieniu kontenera, zanim wykona pierwszą kontrolę stanu. Daje to aplikacji czas na prawidłową inicjalizację.

Po wdrożeniu tej konfiguracji możesz sprawdzić kondycję kontenera, uruchamiając `docker ps`. W kolumnie stanu wyświetli się `(healthy)`, jeśli kontrola stanu zakończy się pomyślnie. Jeśli kontener stanie się niezdrowy, platforma Docker automatycznie uruchomi go ponownie w oparciu o zasady `restart` (np. `unless-stopped`).
