# Zugriff auf die Web-UI

Sobald der DockFlare-Container erfolgreich gestartet wurde, können Sie die Web-UI aufrufen, um Ihre Einstellungen zu verwalten, den Status Ihrer Tunnel einzusehen und Ingress-Regeln manuell zu konfigurieren.

## Standard-URL

Standardmäßig ist die DockFlare-Web-UI über Port `5000` erreichbar. Öffnen Sie dazu Ihren Webbrowser und rufen Sie folgende URL auf:

```
http://<your-server-ip>:5000
```

Ersetzen Sie `<your-server-ip>` durch die IP-Adresse des Servers, auf dem DockFlare ausgeführt wird.

## Ersteinrichtung

Beim ersten Aufruf der Web-UI führt Sie der **Assistent für die Ersteinrichtung** durch die Konfiguration. Dabei hilft er Ihnen bei folgenden Schritten:

1.  Wiederherstellung aus einem vorhandenen DockFlare-Backup (`dockflare_backup_*.zip`). Wenn Sie diese Option wählen, importiert das System Ihre verschlüsselte Konfiguration, den Status und die Agent-Schlüssel und startet den Container anschließend automatisch neu.
2.  Erstellen eines Administratorkontos und eines Passworts für die Web-UI.
3.  Angabe Ihrer Cloudflare-Konto-ID, Zonen-ID (optional) und Ihres API-Tokens.
4.  Bestätigen der Tunneleinstellungen und Abschließen der Onboarding-Schritte.

## Anmeldung

Nach der ersten Einrichtung wird Ihnen bei jedem Zugriff auf die Web-UI ein Anmeldebildschirm angezeigt. Melden Sie sich mit dem Passwort an, das Sie während der Einrichtung festgelegt haben.

## Passwort-Anmeldung deaktivieren

DockFlare enthält die Einstellung „Passwort-Anmeldung deaktivieren“ für fortgeschrittene Bereitstellungen, bei denen DockFlare selbst bereits durch eine externe Authentifizierungsschicht wie Cloudflare Access geschützt ist. **Für die meisten Bereitstellungen raten wir ausdrücklich davon ab.**

### Warum es diese Einstellung gibt

Wenn Sie DockFlare hinter Cloudflare Access oder einem anderen Authentifizierungs-Proxy betreiben, der SSO bereits vor dem Zugriff auf die Anwendung erzwingt, können Sie die integrierte Passwort-Anmeldung von DockFlare deaktivieren, um doppelte Anmeldung zu vermeiden.

### Sicherheitsrisiken bei aktivierter Option

- ⚠️ **Alle API-Endpunkte sind ohne Authentifizierung erreichbar**, wenn diese Einstellung aktiviert ist.
- ⚠️ **Sichtbarkeit im Docker-Netzwerk:** Selbst wenn DockFlare im öffentlichen Internet durch Cloudflare Access geschützt ist, können Container im selben Docker-Netzwerk die externe Authentifizierung umgehen und direkt auf die DockFlare-API zugreifen.
- ⚠️ **Keine eigene Durchsetzung der Authentifizierung:** Die Anwendung geht davon aus, dass die externe Authentifizierung den Schutz vollständig übernimmt.

### Beispiel für einen Angriffsweg

```
Internet → Cloudflare Access (Protected) → DockFlare ✅
         ↓
Docker Network → Other Container → DockFlare API (Unprotected) ❌
```

Auch wenn DockFlare über Cloudflare Access vom Internet abgeschirmt ist, kann jeder Container im selben Docker-Netzwerk diesen Schutz umgehen und ohne Authentifizierung direkt auf die API-Endpunkte zugreifen.

### Empfohlene Vorgehensweise

Anstatt die Passwort-Anmeldung zu deaktivieren, verwenden Sie eine dieser sicheren Optionen:

1. **Lokale DockFlare-Zugangsdaten** - Einfache, in DockFlare integrierte Passwort-Authentifizierung
2. **OAuth/OIDC-Anbieter** - Konfigurieren Sie Google, GitHub, Azure AD oder andere Identitätsanbieter für komfortables Single Sign-On ohne Sicherheitsverlust (siehe [OAuth-Anbieter-Einrichtung](OAuth-Provider-Setup.md))

Beide Optionen bieten eine saubere Authentifizierung und erhalten gleichzeitig den Komfort von SSO. Mit OAuth erhalten Sie Single Sign-On, ohne die Sicherheitsrisiken einer deaktivierten Authentifizierung in Kauf zu nehmen.

### Fazit

Sofern Sie keine sehr spezifische und gut verstandene Sicherheitsarchitektur mit sauberer Netzwerkisolierung haben, sollten Sie die Passwort-Anmeldung aktiviert lassen und für mehr Komfort OAuth verwenden.
