# Zrozumienie Graceful Deletion

Kiedy zatrzymasz kontener zarządzany przez DockFlare, możesz zauważyć, że odpowiadająca mu publiczna nazwa hosta nie przechodzi natychmiast w tryb offline. Dzieje się tak dzięki funkcji **Graceful Deletion**.

## Czym jest Graceful Deletion?

Zamiast natychmiast usuwać regułę ingress w Cloudflare Tunnel i rekord DNS w momencie zatrzymania kontenera, DockFlare oznacza regułę jako `pending_deletion` i uruchamia licznik czasu.

Powiązane zasoby Cloudflare (reguła ingress i rekord DNS) zostaną trwale usunięte dopiero po upływie tego licznika czasu, zwanego **okresem karencji**.

## Dlaczego jest to przydatne?

Ta funkcja ma na celu zapobieganie przerwom w świadczeniu usług w typowych scenariuszach operacyjnych:

* **Aktualizacje kontenera:** Kiedy aktualizujesz obraz kontenera (`docker compose up -d`), Docker zazwyczaj zatrzymuje stary kontener i uruchamia nowy. Bez okresu karencji Twoja usługa byłaby niedostępna przez krótki czas. Dzięki Graceful Deletion rekord DNS i reguła ingress pozostają aktywne, a DockFlare po prostu ponownie kojarzy je z nowym kontenerem, co ogranicza przestój.
* **Tymczasowe ponowne uruchomienie:** jeśli musisz zatrzymać kontener na chwilę, aby zmienić ustawienia, a następnie uruchomić go ponownie, okres karencji gwarantuje, że konfiguracja dostępna publicznie pozostanie nienaruszona.

## Zmienna `GRACE_PERIOD_SECONDS`

Czas trwania tego okresu karencji jest kontrolowany przez zmienną środowiskową `GRACE_PERIOD_SECONDS`, którą możesz ustawić w pliku `docker-compose.yml`.

* Wartość domyślna to `600` sekund (10 minut).
* Możesz dostosować tę wartość do swoich potrzeb. Krótszy okres przyspiesza czyszczenie, a dłuższy okres zapewnia większe okno na ponowne uruchomienie kontenera.

**Przykład:**
```yaml
services:
  dockflare:
    image: alplat/dockflare:stable
    # ... other settings
    environment:
      - GRACE_PERIOD_SECONDS=3600 # Set a 1-hour grace period
```

## Jak to działa w praktyce

1. **Kontener zatrzymany:** Uruchamiasz `docker stop my-app`.
2. **Oczekujące na usunięcie:** DockFlare wykrywa zdarzenie zatrzymania. W panelu administracyjnym reguła `my-app.example.com` będzie teraz wyświetlać status **`pending_deletion`** oraz planowany czas usunięcia.
3. **Dwa scenariusze:**
    * **Scenariusz A: Wygaśnięcie okresu karencji:** Jeśli kontener pozostanie zatrzymany i upłynie okres karencji (np. 10 minut), uruchomione zostanie zadanie czyszczenia w tle DockFlare. Spowoduje to usunięcie reguły ingress z Cloudflare Tunnel i usunięcie rekordu DNS CNAME.
    * **Scenariusz B: Ponowne uruchomienie kontenera:** Jeśli uruchomisz kontener ponownie (`docker start my-app`) **przed** upłynięciem okresu karencji, DockFlare wykryje zdarzenie startu. Zobaczy, że reguła ma status `pending_deletion`, anuluje usunięcie i zmieni jej status z powrotem na **`active`**. Usługa pozostanie dostępna.
