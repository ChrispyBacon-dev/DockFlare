# Verwendung der Web-UI

Die DockFlare Web-UI ist ein mächtiges Werkzeug zur Verwaltung, Überwachung und Konfiguration Ihrer Dienste. Sie bietet eine benutzerfreundliche Oberfläche für Aufgaben, die über einfache Docker-Label-Konfigurationen hinausgehen.

## Das Dashboard (Hauptseite)

Die erste Seite nach dem Einloggen ist das Haupt-Dashboard. Dies ist die zentrale Anlaufstelle zur Ansicht des Zustands all Ihrer verwalteten Dienste.

*   **Tabelle der verwalteten Ingress-Regeln:** Diese Tabelle listet jede Ingress-Regel auf, die von DockFlare gemanagt wird, unabhängig davon, ob sie aus einem Docker-Container stammt oder manuell angelegt wurde.
    *   **Hostname:** Der öffentlich zugängliche Name des Dienstes.
    *   **Service:** Die interne Ziel-URL.
    *   **Source:** Gibt an, ob die Regel von `Docker` stammt oder `Manually` in der UI angelegt wurde.
    *   **Status:** Zeigt an, ob die Regel `active`, `pending_deletion` (ausstehende Löschung) ist oder einen `UI Override` (Überschreibung) besitzt.
    *   **Access:** Zeigt die angewandte Access Group und den Modus-Badge an. Erwarten Sie `Public`- oder `Authenticated`-Plaketten, Gruppennamen und Schnelllinks zum Cloudflare-Dashboard, falls die Richtlinien synchronisiert sind.
    *   **Manage Rule:** Mit diesem Button können Sie jede Regel direkt bearbeiten.
*   **Echtzeit-Logs:** Unter der Tabelle finden Sie eine Echtzeit-Log-Ansicht, die Ausgaben des DockFlare-Backends streamt, was zur Fehlersuche von unschätzbarem Wert ist.

## Regeln verwalten

Die UI gibt Ihnen volle Kontrolle über Ihre Ingress-Regeln.

*   **Manuelle Regel hinzufügen:** Über den Button "Add Manual Rule" können Sie Ingress-Regeln für Dienste erstellen, die nicht in Docker laufen (z.B. ein Dienst auf einem anderen PC in Ihrem LAN). Über das Formular definieren Sie den Hostnamen, die Service-URL und optional eine Access Group.
*   **Jede Regel bearbeiten:** Ein Klick auf "Manage Rule" neben einer beliebigen Regel öffnet ein Fenster zur Konfigurationsanpassung. Hierdurch können Sie Docker-Labels über die Benutzeroberfläche übersteuern.
*   **Auf Labels zurücksetzen:** Hat eine von Docker stammende Regel einen UI-Override, erscheint der Button "Revert to Labels" (Auf Labels zurücksetzen). Ein Klick verwirft die manuellen Änderungen, sodass die Regel wieder ihren Docker-Labels folgt.

## Access Policies Seite

Diese Seite ist der zentrale Ort zur Verwaltung Ihrer wiederverwendbaren **Access Groups** und zur Absicherung Ihrer DNS-Zonen mitsamt Wildcard-Richtlinien.

### Advanced Access Policies (Erweiterte Zugriffsrichtlinien)

Aus dem Bereich der Access Groups können Sie:
*   Neue Access Groups **erstellen** (Modal mit zwei Tabs: Authenticated vs. Public). Hinweisbanner helfen dabei zu verstehen, wann DockFlare eine Cloudflare-Entscheidung `allow` oder `bypass` erzeugt.
*   Bestehende Access Groups **bearbeiten**. Die UI erzwingt modusabhängige Validierung (z.B. E-Mails sind bei Authenticated erforderlich).
*   Access Groups, die keine Verwendung mehr finden, **löschen** (Systemrichtlinien wie `public-default-bypass` bleiben unveränderlich).
*   **Sync from Cloudflare** ausführen, um bestehende DockFlare-Policies aus Ihrem Cloudflare-Account zu importieren.
*   Über das Aktionsmenü neben einem Eintrag die zugehörige Policy im Cloudflare-Dashboard öffnen (Cloudflare-Icon).

**Hinweis:** Die Systemrichtlinie `public-default-bypass` wird automatisch erstellt und von DockFlare verwaltet.

### Zone Default Policies (*.tld Wildcards)

Die zweite Sektion zeigt **Zone Default Policies**: ein Sicherheits-Best-Practice-Feature, das alle Subdomains einer Zone per Wildcard-Policy schützt:

*   **Schutzstatus:** Badges weisen hin, welche Zonen `*.domain.com` Wildcard Policies innehaben (Protected 🛡️) und welche nicht (Not Protected ⚠️).
*   **Zonenrichtlinie erstellen:** "Create Policy" erzeugt für ungeschützte Zonen eine Wildcard-Access-Application.
*   **Policy auswählen:** Legen Sie fest, welche Access Group alle Subdomains schützen soll (Public Bypass, Authenticated oder eigene Policy).
*   **Sicherheitsnetz:** Selbst wenn Sie für einen einzelnen Service keine Policy setzen, greift die Zonen-Wildcard und verhindert unbeabsichtigte Exponierung.

**Best Practice:** Erstellen Sie Zonen-Standardrichtlinien für alle Domains. Für öffentliche Domains nutzen Sie `public-default-bypass`, für interne/private Domains eine Authentifizierungs-Policy. So bleibt keine Subdomain versehentlich ungeschützt.

Weitere Details unter [Best Practices & Beispiele für Zugriffsrichtlinien](Access-Policy-Best-Practices.md).

## Einstellungsseite

Die Seite **Settings** (Einstellungen) enthält administrative und zentrale Konfigurationsoptionen:

*   **Cloudflare Tunnels:** Listet alle Cloudflare Tunnels in Ihrem Account, deren Status und die verbundenen `cloudflared` Agents. Außerdem sehen Sie CNAME-DNS-Records, die auf Ihre Tunnels zeigen.
*   **Backup & Restore:** Download eines vollständigen DockFlare-Backups (`.zip` mit verschlüsselter Konfiguration, Agent Keys und State) oder Upload eines zuvor exportierten Archivs zur Wiederherstellung.
*   **Sicherheit:**
    *   **Change Password (Passwort ändern):** Tauschen Sie hier Ihr Zugriffskennwort zur UI.
    *   **Disable Password Login (Passwort-Login deaktivieren):** Für fortgeschrittene Setups, in denen DockFlare hinter einer externen Authentifizierungsschicht läuft. **⚠️ Warnung:** Das erzeugt ein Risiko durch Docker-Netzwerk-Exposure: Container im selben Netzwerk können externe Authentifizierung umgehen und direkt auf die DockFlare-API zugreifen. Nutzen Sie stattdessen nach Möglichkeit OAuth/OIDC für SSO. Details siehe [Zugriff auf die Web-UI](Accessing-the-Web-UI.md#passwort-anmeldung-deaktivieren).
*   **Cloudflare Credentials:** Dient dem Wechsel der Account ID und des API Tokens, falls notwendig.
*   **Core Configuration:** Grundeinstellungen wie Tunnel-Name und Rule Grace Period.
