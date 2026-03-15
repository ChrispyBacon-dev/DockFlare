# Witamy w dokumentacji DockFlare!

DockFlare to samodzielnie hostowany kontroler ingressu, który upraszcza zarządzanie Cloudflare Tunnel i Zero Trust. Wykorzystuje etykiety Dockera do automatycznej konfiguracji, a jednocześnie udostępnia rozbudowany panel administracyjny do ręcznego definiowania usług i nadpisywania zasad.

Niniejsza dokumentacja zawiera wyczerpujące informacje na temat DockFlare. Niezależnie od tego, czy jesteś nowym, czy doświadczonym użytkownikiem, znajdziesz wszystko, co musisz wiedzieć, aby w pełni wykorzystać DockFlare.

## Spis treści

* **[Strona główna](Home.md)**
* **Pierwsze kroki**
    * [Wymagania wstępne](Prerequisites.md)
    * [Szybki start (Docker Compose)](Quick-Start-Docker-Compose.md)
    * [Dostęp do panelu administracyjnego](Accessing-the-Web-UI.md)
* **Podstawowe pojęcia**
    * [Jak działa DockFlare](How-DockFlare-Works.md)
    * [Agent DockFlare i architektura wieloserwerowa](Multi-Server-Agent.md)
    * [Sprawdzone praktyki dotyczące zasad dostępu](Access-Policy-Best-Practices.md)
    * [Domyślne zasady strefy](Zone-Default-Policies.md)
    * [Wewnętrzny i zewnętrzny `cloudflared`](Internal-vs-External-cloudflared.md)
    * [Trwałość stanu](State-Persistence.md)
* **Konfiguracja**
    * [Etykiety kontenerów](Container-Labels.md)
    * [Dostawcy tożsamości](Identity-Providers.md)
    * [Konfiguracja dostawcy OAuth](OAuth-Provider-Setup.md)
* **Przewodnik użytkowania**
    * [Podstawowe użycie (jedna domena)](Basic-Usage-Single-Domain.md)
    * [Korzystanie z wielu domen (indeksowanych etykiet)](Using-Multiple-Domains-Indexed-Labels.md)
    * [Korzystanie z domen wildcard](Using-Wildcard-Domains.md)
    * [Zarządzanie strefami DNS](Managing-DNS-Zones.md)
    * [Graceful Deletion](Understanding-Graceful-Deletion.md)
    * [Korzystanie z panelu administracyjnego](Using-the-Web-UI.md)
    * [Kopia zapasowa i przywracanie](Backup-and-Restore.md)
* **Tematy zaawansowane**
    * [Tryb zewnętrzny `cloudflared`](External-cloudflared-Mode.md)
    * [Przełączanie między trybami](Switching-Between-Modes.md)
    * [Monitorowanie za pomocą Prometheusa i Grafany](Monitoring-with-Prometheus-&-Grafana.md)
    * [Dostrajanie wydajności](Performance-Tuning.md)
    * [Polityka bezpieczeństwa treści (CSP)](Content-Security-Policy.md)
    * [Architektura bezpieczeństwa i wzmacnianie zabezpieczeń](Security-Architecture.md)
* **Rozwiązywanie problemów**
    * [Typowe problemy](Common-Issues.md)
    * [Debugowanie i dzienniki](Debugging-&-Logs.md)
    * [Kontrola stanu](Health-Checks.md)
    * [Narzędzia CLI](CLI-Utilities.md)
* **[Współtworzenie](Contributing.md)**
* **[Licencja](License.md)**
