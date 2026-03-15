# Wewnętrzny a zewnętrzny `cloudflared`

DockFlare może działać w dwóch trybach zarządzania agentem `cloudflared`, czyli oprogramowaniem, które faktycznie tworzy trwałe połączenie pomiędzy Twoim serwerem a siecią Cloudflare. Zrozumienie tych dwóch trybów jest kluczem do wyboru właściwej konfiguracji dla Twojego środowiska.

## Tryb wewnętrzny (domyślny)

W trybie wewnętrznym DockFlare bierze pełną odpowiedzialność za zarządzanie agentem `cloudflared`.

### Jak to działa
Po uruchomieniu DockFlare automatycznie:
1. Utwórz dedykowany kontener Docker z obrazem `cloudflare/cloudflared`.
2. Skonfiguruj ten kontener agenta, aby łączył się z Twoim kontem Cloudflare i korzystał z tunelu określonego w ustawieniach DockFlare.
3. Upewnij się, że agent jest uruchomiony i uruchom go ponownie, jeśli zakończy się niepowodzeniem.
4. Automatycznie zastosuj odpowiednie ustawienia, takie jak włączenie punktu końcowego metryk Prometheus.

Jest to **tryb domyślny i zalecany** dla większości użytkowników.

### Zalety
* **Prostota:** Jest to konfiguracja „zero konfiguracji”. DockFlare zajmie się wszystkim za Ciebie.
* **Gwarantowana kompatybilność:** DockFlare zapewnia, że agent jest skonfigurowany w sposób, z którym może współpracować.
* **Scentralizowane zarządzanie:** Wszystko związane z Twoimi tunelami jest zarządzane przez DockFlare.

### Wady
* **Mniejsza kontrola:** Masz ograniczoną kontrolę nad konfiguracją agenta `cloudflared` poza tym, co udostępnia DockFlare.

---

## Zewnętrzny tryb `cloudflared`

W trybie zewnętrznym jesteś odpowiedzialny za samodzielne uruchamianie agenta `cloudflared` i zarządzanie nim. DockFlare połączy się z istniejącym agentem zamiast tworzyć własnego.

### Jak to działa
DockFlare **nie** utworzy kontenera `cloudflared`. Zamiast tego zakłada, że masz agenta `cloudflared` działającego w miejscu, z którego może skorzystać. Może to być:
* Proces `cloudflared` działający bezpośrednio w systemie operacyjnym hosta (np. jako usługa `systemd`).
* Kontener `cloudflared`, którym zarządzasz samodzielnie za pomocą osobnego pliku `docker-compose.yml` lub polecenia uruchomienia Dockera.
* Agent `cloudflared` działający na zupełnie innym komputerze.

Jest to **tryb zaawansowany** przeznaczony dla użytkowników o określonych potrzebach lub złożonych istniejących konfiguracjach.

### Zalety
* **Maksymalna kontrola:** masz pełną kontrolę nad agentem `cloudflared`, w tym nad jego wersją, argumentami wiersza poleceń i cyklem życia.
* **Integracja z istniejącymi konfiguracjami:** Idealna, jeśli masz już agenta `cloudflared` działającego do innych celów.
* **Oddzielenie:** Oddziela cykl życia DockFlare od cyklu życia agenta `cloudflared`.

### Wady
* **Złożoność:** Odpowiadasz za upewnienie się, że agent `cloudflared` działa, jest poprawnie skonfigurowany i podłączony do prawidłowego tunelu.
* **Narzuty konfiguracyjne:** Aby używać tego agenta zewnętrznego, musisz skonfigurować DockFlare.

### Jak włączyć tryb zewnętrzny
Aby włączyć tryb zewnętrzny, należy ustawić następujące zmienne środowiskowe dla kontenera DockFlare:

* `USE_EXTERNAL_CLOUDFLARED=true`: Włącza tryb zewnętrzny.
* `EXTERNAL_TUNNEL_ID`: musi to być ustawione na UUID tunelu, do używania którego skonfigurowany jest zewnętrzny agent `cloudflared`.

Kiedy te zmienne są ustawione, DockFlare pominie wewnętrzne zarządzanie agentami i zamiast tego wyśle wszystkie konfiguracje reguł ingress do tunelu określonego przez `EXTERNAL_TUNNEL_ID`.
