# Vitaj v dokumentácii DockFlare!

DockFlare je výkonný, samostatne hostovaný ingress kontrolér, ktorý zjednodušuje správu Cloudflare Tunnel a Zero Trust. Na automatickú konfiguráciu využíva Docker labely a zároveň ponúka prepracované webové rozhranie na manuálne definovanie služieb a prepisovanie politík.

Táto dokumentácia poskytuje komplexné informácie o DockFlare. Či už si nový alebo skúsený používateľ, nájdeš tu všetko, čo potrebuješ vedieť, aby si z DockFlare vyťažil maximum.

## Obsah

*   **[Domov](Home.md)**
*   **Začíname**
    *   [Predpoklady](Prerequisites.md)
    *   [Rýchly štart (Docker Compose)](Quick-Start-Docker-Compose.md)
    *   [Prístup k webovému rozhraniu](Accessing-the-Web-UI.md)
*   **Základné pojmy**
    *   [Ako DockFlare funguje](How-DockFlare-Works.md)
    *   [Agent DockFlare a viacserverová architektúra](Multi-Server-Agent.md)
    *   [Osvedčené postupy pre prístupové politiky](Access-Policy-Best-Practices.md)
    *   [Predvolené politiky zóny](Zone-Default-Policies.md)
    *   [Interný vs. externý `cloudflared`](Internal-vs-External-cloudflared.md)
    *   [Trvalé uloženie stavu](State-Persistence.md)
*   **Konfigurácia**
    *   [Docker labely](Container-Labels.md)
    *   [Poskytovatelia identity](Identity-Providers.md)
    *   [Nastavenie poskytovateľa OAuth](OAuth-Provider-Setup.md)
*   **Návod na použitie**
    *   [Základné použitie (jedna doména)](Basic-Usage-Single-Domain.md)
    *   [Použitie viacerých domén (indexované labely)](Using-Multiple-Domains-Indexed-Labels.md)
    *   [Použitie domén s wildcardom](Using-Wildcard-Domains.md)
    *   [Správa DNS zón](Managing-DNS-Zones.md)
    *   [Ako funguje riadené odstránenie (graceful deletion)](Understanding-Graceful-Deletion.md)
    *   [Používanie webového rozhrania](Using-the-Web-UI.md)
    *   [Záloha a obnovenie](Backup-and-Restore.md)
*   **E-mailová sada**
    *   [Prehľad a architektúra](Email-Overview.md)
    *   [Predpoklady a nastavenie CF](Email-Prerequisites.md)
    *   [Nasadenie cez Docker](Email-Docker-Deployment.md)
    *   [Konfigurácia domény](Email-Domain-Setup.md)
    *   [Správa schránok a kvót](Email-Mailbox-Management.md)
    *   [Používanie webmailu (PWA)](Email-Using-Webmail.md)
    *   [Údržba a riešenie problémov](Email-Maintenance.md)
*   **Pokročilé témy**
    *   [Externý režim `cloudflared`](External-cloudflared-Mode.md)
    *   [Prepínanie medzi režimami](Switching-Between-Modes.md)
    *   [Monitoring: Prometheus a Grafana](Monitoring-with-Prometheus-&-Grafana.md)
    *   [Ladenie výkonu](Performance-Tuning.md)
    *   [Content Security Policy (CSP)](Content-Security-Policy.md)
    *   [Bezpečnostná architektúra a spevnenie](Security-Architecture.md)
*   **Riešenie problémov**
    *   [Bežné problémy](Common-Issues.md)
    *   [Ladenie a logy](Debugging-&-Logs.md)
    *   [Kontroly stavu](Health-Checks.md)
    *   [CLI nástroje](CLI-Utilities.md)
*   **[Prispievanie](Contributing.md)**
*   **[Licencia](License.md)**
