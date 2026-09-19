# E-Mail-Voraussetzungen & Einrichtung

Bevor Sie die E-Mail-Suite aktivieren, stellen Sie sicher, dass Ihre Umgebung und Ihr Cloudflare-Konto korrekt konfiguriert sind.

## Cloudflare-Anforderungen

1.  **Domain-Verwaltung:** Ihre Domain muss in Cloudflare aktiv sein.
2.  **E-Mail-Routing (Eingehend):** Cloudflare Email Routing ist auf allen Tarifen verfügbar, einschließlich Free. DockFlare konfiguriert die erforderlichen MX-, SPF- und DMARC-Einträge automatisch.
3.  **E-Mail-Versand (Ausgehend):** Cloudflare Email Sending befindet sich derzeit in der Beta-Phase. DockFlare konfiguriert die DKIM-Signierschlüssel und die Versandsubdomain automatisch. Für den Versand an externe Adressen ist jedoch Folgendes erforderlich:
    - Ein **Cloudflare Workers Paid Plan** (5 $/Monat).
    - Manuelle Aktivierung von **CF Email Sending (Beta)** im Cloudflare-Dashboard unter **E-Mail → E-Mail-Versand**.
    - Ohne diese Schritte ist der ausgehende Versand auf verifizierte Cloudflare-Adressen beschränkt.
4.  **R2-Speicher:** R2 muss in Ihrem Cloudflare-Dashboard aktiviert sein. R2 beinhaltet ein kostenloses Kontingent von 10 GB; zur Aktivierung kann jedoch eine Zahlungsmethode erforderlich sein.

## API-Token-Berechtigungen

Die E-Mail-Suite benötigt zusätzliche Berechtigungen für Ihr vorhandenes DockFlare-API-Token. Aktualisieren Sie es unter **Benutzerprofil > API-Token** und fügen Sie folgende Berechtigungen hinzu:

| Bereich | Spezifische Berechtigung | Zugriffsebene | Zweck |
| :--- | :--- | :--- | :--- |
| **Account** | **Workers Scripts** | **Bearbeiten** | Bereitstellung von Inbound-/Outbound-Workern |
| **Account** | **Workers KV Storage** | **Bearbeiten** | Echtzeit-Quota-Durchsetzung am Edge |
| **Account** | **R2 Storage** | **Bearbeiten** | Erstellen und Verwalten von Transit-Buckets |
| **Account** | **Access: Apps and Policies** | **Bearbeiten** | Bypass-Richtlinie für den eingehenden E-Mail-Webhook-Pfad erstellen, wenn Webmail durch Cloudflare Access geschützt ist |
| **Zone** | **E-Mail-Routing** | **Bearbeiten** | Routing aktivieren und Regeln verwalten |
| **Zone** | **DNS** | **Bearbeiten** | Erstellen von MX-, SPF-, DMARC- und DKIM-Einträgen |

> **Sicherheitshinweis:** Es wird dringend empfohlen, die „Account Resources" und „Zone Resources" dieses Tokens auf das spezifische Konto und die Domains zu beschränken, die Sie mit DockFlare verwenden möchten.

## Systemanforderungen

*   **DockFlare:** v3.1.0 oder höher.
*   **Docker:** v20.10+.
*   **Docker Compose:** v2.20+ (erforderlich für `profiles`-Unterstützung).
*   **Speicherplatz:** Stellen Sie sicher, dass auf dem Host-System ausreichend Speicherplatz für das `mail_data`-Volume vorhanden ist, in dem alle E-Mail-Datenbanken und Anhänge gespeichert werden.
