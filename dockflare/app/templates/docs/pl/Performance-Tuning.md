# Strojenie wydajności

W przypadku zdecydowanej większości użytkowników domyślne ustawienia DockFlare zapewniają dobrą równowagę wydajności i wykorzystania zasobów. Jednakże w bardzo dużych lub bardzo dynamicznych środowiskach korzystne może być dostrojenie niektórych zaawansowanych parametrów związanych z wydajnością.

Te ustawienia są konfigurowane za pomocą zmiennych środowiskowych w pliku `docker-compose.yml`.

---

## `CLEANUP_INTERVAL_SECONDS`

Ta zmienna kontroluje częstotliwość uruchamiania zadania DockFlare w tle w celu oczyszczenia wygasłych zasobów (tj. reguł z zatrzymanych kontenerów, których okres karencji upłynął).

* **Domyślnie:** `60` sekund
* **Opis:** Krótszy interwał oznacza, że nieaktualne zasoby są szybciej usuwane z konfiguracji Cloudflare. Dłuższy interwał zmniejsza częstotliwość sprawdzania w tle, co może nieznacznie zmniejszyć zużycie zasobów.
* **Kiedy dostroić:** Jeśli masz bardzo dynamiczne środowisko z wieloma krótkotrwałymi kontenerami i chcesz, aby ich zasoby zostały wyczyszczone niemal natychmiast, możesz obniżyć tę wartość (np. do `30`). Dla większości użytkowników ustawienie domyślne jest w porządku.

**Przykład:**
```yaml
environment:
  - CLEANUP_INTERVAL_SECONDS=30
```

---

## `MAX_CONCURRENT_DNS_OPS`

Ta zmienna ustawia maksymalną liczbę jednoczesnych operacji DNS (tworzenie, usuwanie), które DockFlare wykona jednocześnie.

* **Domyślnie:** `3`
* **Opis:** Jest to pokrętło do bezpośredniego dostrajania wydajności dla środowisk z dużą liczbą usług. Podczas uruchamiania DockFlare lub gdy uruchamianych jest wiele kontenerów jednocześnie, to ustawienie ogranicza liczbę równoległych żądań wysyłanych do API Cloudflare w celu wprowadzenia zmian w DNS.
* **Kiedy dostroić:** Jeśli zarządzasz setkami usług i zauważysz, że początkowe uruchomienie lub masowe wdrożenie jest powolne w celu utworzenia wszystkich rekordów DNS, możesz spróbować zwiększyć tę wartość (np. do `5` lub `10`). Należy pamiętać, że ustawienie zbyt dużej wartości może prowadzić do ograniczenia szybkości interfejsu Cloudflare API.

**Przykład:**
```yaml
environment:
  - MAX_CONCURRENT_DNS_OPS=5
```

---

## `RECONCILIATION_BATCH_SIZE`

Kontroluje to wielkość partii dla różnych zadań uzgadniania w tle.

* **Domyślnie:** `3`
* **Opis:** Niektóre zadania w tle w DockFlare przetwarzają elementy partiami, aby uniknąć przeciążenia systemu lub interfejsu API Cloudflare. To ustawienie kontroluje wielkość tych partii.
* **Kiedy dostrajać:** Jest to bardzo zaawansowane ustawienie. W przypadku większości użytkowników wartość domyślna nie powinna być zmieniana. Jeśli masz bardzo dużą liczbę reguł (wiele setek lub tysięcy), możesz poeksperymentować z nieco większym rozmiarem partii, ale generalnie nie jest to konieczne.

**Przykład:**
```yaml
environment:
  - RECONCILIATION_BATCH_SIZE=5
```

---

## `SCAN_ALL_NETWORKS`

Ta zmienna zmienia sposób, w jaki DockFlare odkrywa adresy IP kontenerów.

* **Domyślnie:** `false`
* **Opis:** DockFlare domyślnie oczekuje, że kontener docelowy znajduje się w tej samej sieci Docker, co sam DockFlare. Gdy `SCAN_ALL_NETWORKS` jest ustawione na `true`, DockFlare sprawdzi wszystkie sieci, do których podłączony jest kontener, aby znaleźć sieć współdzieloną.
* **Kiedy dostroić:** Tę opcję należy włączyć tylko w przypadku złożonej konfiguracji sieci Docker, w której kontenery aplikacji nie znajdują się w tej samej sieci co DockFlare. Należy pamiętać, że włączenie tej opcji może mieć wpływ na wydajność w środowiskach z bardzo dużą liczbą sieci Docker, ponieważ wymaga więcej pracy inspekcyjnej ze strony DockFlare.

**Przykład:**
```yaml
environment:
  - SCAN_ALL_NETWORKS=true
```
