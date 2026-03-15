# Verwendung der Web UI

Die DockFlare Web UI isch ein mächtiges Werkzeug zur Verwaltung, Überwachung u Konfiguration dinere Dienste. Si bietet eine benutzerfreundliche Oberfläche für Aufgaben, die über einfache Docker-Label-Konfigurationen hinausgehen.

## Das Dashboard (Hauptseite)

Die erste Seite nach dem Einloggen isch das Haupt-Dashboard. Das isch die zentrale Anlaufstelle zur Ansicht des Zustands all dinere verwalteten Dienste.

*   **Tabelle der verwalteten Ingress-Regeln:** Diese Tabelle listet jede Ingress-Regel auf, die von DockFlare gemanagt wird, unabhängig davon, öb sie aus einem Docker-Container stammt oder manuell angelegt wurde.
    *   **Hostname:** Der öffentlich zugängliche Name des Dienstes.
    *   **Service:** Die interne Ziel-URL.
    *   **Source:** Gibt an, öb die Regel von `Docker` stammt oder `Manually` in der UI angelegt wurde.
    *   **Status:** Zeigt an, öb die Regel `active`, `pending_deletion` (ausstehende Löschung) isch oder einen `UI Override` (Überschreibung) besitzt.
    *   **Access:** Zeigt die angewandte Access Group u den Modus-Badge an. Erwart `Public`- oder `Authenticated`-Plaketten, Gruppennamen u Schnelllinks zum Cloudflare-Dashboard, falls die Richtlinien synchronisiert si.
    *   **Manage Rule:** Mit diesem Button chasch jede Regel direkt bearbeiten.
*   **Echtzeit-Logs:** Unter der Tabelle findsch eine Echtzeit-Log-Ansicht, die Ausgaben des DockFlare-Backends streamt, was zur Fehlersuche von unschätzbarem Wert isch.

## Regeln verwalten

Die UI gibt dir volle Kontrolle über dini Ingress-Regeln.

*   **Manuelle Regel hinzufügen:** Über den Button "Add Manual Rule" chasch Ingress-Regeln für Dienste erstellen, die nid in Docker laufen (z.B. e Dienst uf eme angere PC i dim LAN). Im Formular gisch du de Hostname, d'Service-URL u optional e Access Group aa.
*   **Jede Regel bearbeiten:** Ein Klick auf "Manage Rule" neben einer beliebigen Regel öffnet es Fenster für d'Konfiguration. So chasch Docker-Labels über d'UI übersteuere.
*   **Auf Labels zurücksetzen:** Hat eine von Docker stammende Regel einen UI-Override, erscheint der Button "Revert to Labels" (Auf Labels zurücksetzen). Ein Klick verwirft die manuellen Änderungen, sodass die Regel wieder ihren Docker-Labels folgt.

## Access Policies Seite

Die Siite isch der zentrale Ort zur Verwaltung dinere wiederverwendbaren **Access Groups** u zur Absicherung dinere DNS-Zonen mitsamt Wildcard-Richtlinien.

### Advanced Access Policies (Erweiterte Zugriffsrichtlinien)

Aus dem Bereich der Access Groups chasch:
*   Neue Access Groups **erstellen** (Modal mit zwei Tabs: Authenticated vs. Public). Hinweisbanner helfen dabei zu verstehen, wann DockFlare eine Cloudflare-Entscheidung `allow` oder `bypass` erzeugt.
*   Bestehende Access Groups **bearbeiten**. Die UI erzwingt modusabhängige Validierung (z.B. E-Mails si bei Authenticated nötig).
*   Access Groups, die kener Verwendung mehr finden, **löschen** (Systemrichtlinien wie `public-default-bypass` bleiben unveränderlich).
*   **Sync from Cloudflare** ausführen, um bestehende DockFlare-Policies aus dim Cloudflare-Account zu importieren.
*   Über das Aktionsmenü neben einem Eintrag die zugehörige Policy im Cloudflare-Dashboard ufmache (Cloudflare-Icon).

**Hinweis:** Die Systemrichtlinie `public-default-bypass` wird automatisch erstellt u von DockFlare verwaltet.

### Zone Default Policies (*.tld Wildcards)

Die zweite Sektion zeigt **Zone Default Policies**: ein Sicherheits-Best-Practice-Feature, das alle Subdomains einer Zone per Wildcard-Policy schützt:

*   **Schutzstatus:** Badges weisen hin, welche Zonen `*.domain.com` Wildcard Policies innehaben (Protected 🛡️) u welche nid (Not Protected ⚠️).
*   **Zonenrichtlinie erstellen:** "Create Policy" erzeugt für ungeschützte Zonen eine Wildcard-Access-Application.
*   **Policy auswählen:** Leg fest, welche Access Group alle Subdomains schützen soll (Public Bypass, Authenticated oder eigene Policy).
*   **Sicherheitsnetz:** Selbst wenn du für einen einzelnen Service kener Policy setzen, greift die Zonen-Wildcard u verhindert unbeabsichtigte Exponierung.

**Best Practice:** Erstell Zonen-Standardrichtlinien für alle Domains. Für öffentliche Domains bruuchsch `public-default-bypass`, für interne/private Domains eine Authentifizierungs-Policy. So bleibt kener Subdomain versehentlich ungeschützt.

Weitere Details unter [Best Practices & Beispiele für Zugriffsrichtlinien](Access-Policy-Best-Practices.md).

## Einstellungsseite

Die Seite **Settings** (Istellige) enthält administrative u zentrale Konfigurationsoptionen:

*   **Cloudflare Tunnels:** Listet alle Cloudflare Tunnels in dim Account, deren Status u die verbundenen `cloudflared` Agents. Ausserdem gsehsch CNAME-DNS-Records, die auf dini Tunnels zeigen.
*   **Backup & Restore:** Download eines vollständigen DockFlare-Backups (`.zip` mit verschlüsselter Konfiguration, Agent Keys u State) oder Upload eines zuvor exportierten Archivs zur Wiederherstellung.
*   **Sicherheit:**
    *   **Change Password (Passwort ändern):** Tausch hier din Zugriffskennwort zur UI.
    *   **Disable Password Login (Passwort-Login deaktivieren):** Für fortgschrittni Setups, in denen DockFlare hinter einer externen Authentifizierungsschicht läuft. **⚠️ Warnung:** Das erzeugt ein Risiko durch Docker-Netzwerk-Exposure: Container im selben Netzwerk chöi externe Authentifizierung umgehen u direkt auf die DockFlare-API zugreifen. Bruuch stattdessen nach Möglichkeit OAuth/OIDC für SSO. Details siehe [Zugriff auf die Web UI](Accessing-the-Web-UI.md).
*   **Cloudflare Credentials:** Dient dem Wechsel der Account ID u des API Tokens, falls notwendig.
*   **Core Configuration:** Grundeinstellungen wie Tunnel-Name u Rule Grace Period.
