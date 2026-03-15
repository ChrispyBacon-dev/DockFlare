# Monitorowanie za pomocą Prometheusa i Grafany

Agent `cloudflared` zarządzany przez DockFlare może udostępniać szeroki zakres metryk dotyczących wydajności i kondycji w formacie Prometheus. Zbierając i wizualizując te wskaźniki, możesz uzyskać cenne informacje na temat ruchu w tunelu, opóźnień i współczynników błędów.

W tym przewodniku wyjaśniono, jak włączyć punkt końcowy metryk i przedstawiono szybką konfigurację stosu monitorowania przy użyciu programów Prometheus i Grafana.

## Krok 1: Włącz punkt końcowy metryk w DockFlare

Pierwszym krokiem jest poinformowanie DockFlare, aby włączył punkt końcowy metryk Prometheus na zarządzanym agencie `cloudflared`.

Można to zrobić, ustawiając zmienną środowiskową `CLOUDFLARED_METRICS_PORT` dla kontenera DockFlare.

**Przykład `docker-compose.yml`:**
```yaml
services:
  dockflare:
    image: alplat/dockflare:stable
    # ... other settings
    environment:
      # Enable the metrics endpoint on port 2000 inside the container
      - CLOUDFLARED_METRICS_PORT=2000
```
Po ponownym uruchomieniu DockFlare z tą zmienną automatycznie odtworzy zarządzanego agenta `cloudflared` z włączonym serwerem metryk na określonym porcie.

**Uwaga:** Ta funkcja jest dostępna tylko w domyślnym **Trybie wewnętrznym**. Jeśli korzystasz z [trybu zewnętrznego](External-cloudflared-Mode.md), odpowiadasz za włączenie punktu końcowego metryk na swoim własnym agencie `cloudflared`.

## Krok 2: Skonfiguruj stos monitorowania

Jeśli nie masz jeszcze stosu monitorowania, możesz go szybko skonfigurować za pomocą Docker Compose. Repozytorium DockFlare zawiera przykładową konfigurację w katalogu `/examples`.

Kompletny przewodnik dotyczący konfiguracji Prometheusa i Grafany do monitorowania DockFlare można znaleźć w pliku **[`grafana quick setup.md`](https://github.com/ChrispyBacon-dev/DockFlare/blob/main/examples/grafana%20quick%20setup.md)** w repozytorium.

Ten przewodnik przeprowadzi Cię przez:
1. Utworzenie niezbędnej struktury katalogów.
2. Dodanie usług Prometheus i Grafana do Twojego `docker-compose.yml`.
3. Konfigurowanie Prometheusa do pobierania metryk z agenta `cloudflared`.
4. Automatyczne zaopatrzenie Grafany w źródło danych Prometheus.

## Krok 3: Zaimportuj gotowy pulpit nawigacyjny Grafana

Aby ułatwić wizualizację, DockFlare udostępnia gotowy pulpit nawigacyjny Grafana, który został zaprojektowany tak, aby doskonale współpracował z metrykami udostępnianymi przez agenta `cloudflared`.

1. Panel dostępny jest jako **[`dashboard.json`](https://github.com/ChrispyBacon-dev/DockFlare/blob/main/examples/dashboard.json)** w katalogu `/examples` repozytorium.
2. Pobierz ten plik.
3. Zaloguj się do swojej instancji Grafana.
4. Przejdź do sekcji „Panele informacyjne” i kliknij „Importuj”.
5. Prześlij plik `dashboard.json`.
6. Wybierz źródło danych Prometheus i zaimportuj dashboard.

Będziesz mieć teraz pełny przegląd wydajności tunelu Cloudflare, w tym liczbę żądań, współczynniki błędów, opóźnienia połączenia i inne.

![Przykład panelu Grafana](../static/images/grafana_dashboard_example.png)