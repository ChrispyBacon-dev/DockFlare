# Willkommen in der DockFlare-Dokumentation!

DockFlare ist ein leistungsstarker, selbst gehosteter Ingress-Controller, der die Verwaltung von Cloudflare Tunnel und Zero Trust vereinfacht. Die Konfiguration erfolgt automatisch über Docker-Labels, ergänzt durch eine robuste Web-UI für manuelle Servicedefinitionen und Richtlinienüberschreibungen.

Diese Dokumentation bietet einen umfassenden Überblick über DockFlare. Egal, ob Sie gerade erst anfangen oder bereits Erfahrung mitbringen: Hier finden Sie die wichtigsten Informationen für Einrichtung, Betrieb und Fehlerbehebung.

## Inhaltsverzeichnis

*   **[Startseite](Home.md)**
*   **Erste Schritte**
    *   [Voraussetzungen](Prerequisites.md)
    *   [Schnellstart (Docker Compose)](Quick-Start-Docker-Compose.md)
    *   [Zugriff auf die Web-UI](Accessing-the-Web-UI.md)
*   **Kernkonzepte**
    *   [Wie DockFlare funktioniert](How-DockFlare-Works.md)
    *   [DockFlare-Agent und Multi-Server-Architektur](Multi-Server-Agent.md)
    *   [Best Practices für Zugriffsrichtlinien](Access-Policy-Best-Practices.md)
    *   [Zonen-Standardrichtlinien](Zone-Default-Policies.md)
    *   [Internes vs. externes `cloudflared`](Internal-vs-External-cloudflared.md)
    *   [Persistenz des Status](State-Persistence.md)
*   **Konfiguration**
    *   [Container-Labels](Container-Labels.md)
    *   [Identitätsanbieter](Identity-Providers.md)
    *   [Einrichtung von OAuth-Anbietern](OAuth-Provider-Setup.md)
*   **Benutzerhandbuch**
    *   [Grundlegende Nutzung (Einzelne Domain)](Basic-Usage-Single-Domain.md)
    *   [Nutzung mehrerer Domains (Indizierte Labels)](Using-Multiple-Domains-Indexed-Labels.md)
    *   [Verwendung von Wildcard-Domains](Using-Wildcard-Domains.md)
    *   [Verwaltung von DNS-Zonen](Managing-DNS-Zones.md)
    *   [Graceful Deletion verstehen](Understanding-Graceful-Deletion.md)
    *   [Verwendung der Web-UI](Using-the-Web-UI.md)
    *   [Backup & Wiederherstellung](Backup-and-Restore.md)
*   **Erweiterte Themen**
    *   [Externer `cloudflared`-Modus](External-cloudflared-Mode.md)
    *   [Zwischen den Modi wechseln](Switching-Between-Modes.md)
    *   [Überwachung mit Prometheus & Grafana](Monitoring-with-Prometheus-&-Grafana.md)
    *   [Leistungsoptimierung](Performance-Tuning.md)
    *   [Content-Security-Policy (CSP)](Content-Security-Policy.md)
    *   [Sicherheitsarchitektur & Härtung](Security-Architecture.md)
*   **Fehlerbehebung**
    *   [Häufige Probleme](Common-Issues.md)
    *   [Debugging und Logs](Debugging-&-Logs.md)
    *   [Gesundheitschecks](Health-Checks.md)
    *   [CLI-Dienstprogramme](CLI-Utilities.md)
*   **[Mitwirken](Contributing.md)**
*   **[Lizenz](License.md)**
