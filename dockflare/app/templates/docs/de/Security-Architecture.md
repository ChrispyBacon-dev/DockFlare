# DockFlare Sicherheitsarchitektur und Härtung

Dieses Dokument erläutert, wie DockFlare in Version 3.0+ sowohl den Master-Knoten als auch registrierte Agenten absichert. Es ergänzt das Sicherheitsaudit, indem es die in DockFlare integrierten Schutzmechanismen und empfohlene Betriebspraktiken zusammenfasst.

## 1. Vertrauensmodell der Control Plane

- **Master als maßgebliche Instanz** – Der DockFlare Master verwaltet alle Cloudflare-Zugangsdaten und Richtliniendefinitionen. Agenten verwalten keine API-Tokens selbst, sondern führen Anweisungen aus, die sie über einen authentifizierten Kanal erhalten.
- **API-Schlüssel pro Agent** – Für die Registrierung ist ein eindeutiger API-Schlüssel erforderlich, der vom Master ausgestellt wird. Die Schlüssel werden zusammen mit Metadaten wie Eigentümer, Zeitstempeln und Status verschlüsselt in `agent_keys.dat` gespeichert, sodass sie jederzeit rotiert oder widerrufen werden können.
- **Schutz der Master-API** – Administrative Endpunkte, darunter die Web-UI und `/api/v2/*`, erfordern entweder eine gültige Sitzung oder den Master-API-Schlüssel. Tokens werden in Antworten und Logs maskiert und können ohne Neustart des Stacks rotiert werden.

## 2. Verschlüsselte Konfiguration und Schlüsselverwaltung

- **Verschlüsseltes `dockflare_config.dat`** – Cloudflare-Zugangsdaten, UI-Konten, Tunnel-Standardeinstellungen und der Master-Schlüssel werden in einem verschlüsselten Blob gespeichert, der durch `dockflare.key` geschützt ist.
- **Verschlüsseltes Agentenregister** – API-Schlüssel der Agenten und ihre Audit-Metadaten liegen in `agent_keys.dat`, verschlüsselt mit demselben Fernet-Schlüssel. Sensible Daten erscheinen nicht mehr im Klartext in `state.json`.
- **Automatischer Neustart nach Wiederherstellung** – Wenn ein Backup wiederhergestellt wird, schreibt DockFlare die verschlüsselten Artefakte, lädt den Laufzeitstatus neu, setzt ein Neustart-Flag und beendet sich. Die Docker-Restart-Policy startet den Container anschließend sofort mit der neuen Konfiguration neu.
- **Klartext-`state.json` für Beobachtbarkeit** – `state.json` bleibt bewusst im Klartext, damit Operatoren Regeln und Agenten prüfen können. Für Geheimnisse bleiben die verschlüsselten Dateien maßgeblich.

## 3. Garantien für Backup und Wiederherstellung

- **Inhalt des Archivs** – Jedes Backup-Archiv (`dockflare_backup_*.zip`) enthält `dockflare_config.dat`, `dockflare.key`, `agent_keys.dat`, `state.json` sowie ein `manifest.json` mit Prüfsummen und Versionsmetadaten. Zum Wiederaufbau eines Master-Knotens sind keine weiteren Dateien erforderlich.
- **Automatisierter Wiederherstellungsablauf** – Eine Wiederherstellung über den Einrichtungsassistenten oder die Einstellungsseite schreibt die Artefakte, lädt Laufzeit-Caches neu und erzwingt einen Container-Neustart, damit die verschlüsselte Konfiguration sofort aktiv wird.
- **Abwärtskompatibilität** – Das Hochladen einer einzelnen `state.json` wird weiterhin für Troubleshooting oder Teilmigrationen unterstützt. DockFlare importiert dabei den Laufzeitstatus, behält aber die vorhandene verschlüsselte Konfiguration bei, um versehentliche Zurücksetzungen von Zugangsdaten zu vermeiden.

## 4. Netzwerk- und Kommunikationssicherheit

- **Cloudflare-Tunnel als Transportweg** – Agenten öffnen keine eingehenden Ports. Der gesamte Verkehr läuft über den vom Master verwalteten Cloudflare-Tunnel, wodurch sich die Angriffsfläche auf entfernten Hosts verringert.
- **Authentifizierte Agentenaufrufe** – REST-Aufrufe der Agenten enthalten ihren API-Schlüssel und sind an die registrierte Agent-ID gebunden. Token-Abweichungen oder widerrufene Schlüssel werden abgewiesen.
- **Redis-Backplane** – DockFlare verwendet Redis für Caching, Log-Streaming und Signalisierung zwischen Threads. Der empfohlene Compose-Stack hält Redis in einem eigenen `dockflare-internal`-Netzwerk, sodass Workloads im `cloudflare-net` nicht direkt darauf zugreifen können. Externes Redis sollte mit Authentifizierung und TLS abgesichert werden.
- **Least-Privilege-Laufzeit** – Sowohl der Master als auch die Agenten laufen als Benutzer `dockflare` (UID/GID 65532) und kommunizieren mit Docker ausschließlich über den mitgelieferten Socket-Proxy, wodurch die freigegebene API-Oberfläche klein bleibt.

## 5. Authentifizierung und Autorisierung

- **Abgesicherter UI-Login** – Der Assistent für die Ersteinrichtung erzwingt die Erstellung eines Administratorkontos für die UI. Die Passwort-Anmeldung kann deaktiviert werden, **dies wird jedoch wegen der Sicherheitsrisiken im Docker-Netzwerk dringend nicht empfohlen**.
- **Sitzungsverwaltung** – Flask-Login-Sitzungen sind an die verschlüsselte Konfiguration gebunden. Beim Wiederherstellen eines Backups oder bei einer Rotation von Zugangsdaten werden bestehende Sitzungen automatisch ungültig.
- **Agenten-ACLs** – Jeder Agenteneintrag verfolgt Tunnel-Zuordnung, Heartbeat-Zeitstempel und ausstehende Befehle. Der Master liefert Befehle nur an Agenten aus, die den korrekten Token und einen gueltigen Registrierungsstatus vorweisen.

### ⚠️ Wichtiger Sicherheitshinweis zu „Passwort-Anmeldung deaktivieren“

DockFlare enthält die Einstellung „Passwort-Anmeldung deaktivieren“ für fortgeschrittene Bereitstellungen, bei denen DockFlare selbst durch eine externe Authentifizierungsschicht wie Cloudflare Access geschützt ist. **Für die meisten Bereitstellungen raten wir ausdrücklich davon ab.**

**Sicherheitsrisiken bei aktivierter Option:**
- **Alle API-Endpunkte sind ohne Authentifizierung erreichbar**, wenn diese Einstellung aktiviert ist.
- **Sichtbarkeit im Docker-Netzwerk:** Selbst wenn DockFlare im öffentlichen Internet durch Cloudflare Access geschützt ist, können Container im selben Docker-Netzwerk die externe Authentifizierung umgehen und direkt auf die DockFlare-API zugreifen.
- **Keine Durchsetzung der Authentifizierung:** Die Anwendung geht davon aus, dass die externe Authentifizierung die Sicherheit übernimmt.

**Beispiel für einen Angriffsweg:**
```
Internet → Cloudflare Access (Protected) → DockFlare ✅
         ↓
Docker Network → Other Container → DockFlare API (Unprotected) ❌
```

**Empfohlene Vorgehensweise:**
Anstatt die Passwort-Authentifizierung zu deaktivieren, verwenden Sie eine dieser sicheren Optionen:
1. **Lokale DockFlare-Zugangsdaten** - Einfache, in DockFlare integrierte Passwort-Authentifizierung
2. **OAuth/OIDC-Anbieter** - Konfigurieren Sie Google, GitHub, Azure AD oder andere Identitätsanbieter für komfortables Single Sign-On ohne Sicherheitsverlust

Beide Optionen bieten eine saubere Authentifizierung und erhalten gleichzeitig den Komfort von SSO. Mit OAuth erhalten Sie Single Sign-On, ohne die Sicherheitsrisiken einer deaktivierten Anmeldung in Kauf zu nehmen.

**Fazit:** Sofern Sie keine sehr spezifische und gut verstandene Sicherheitsarchitektur mit sauberer Netzwerkisolierung haben, sollten Sie die Passwort-Anmeldung aktiviert lassen und für mehr Komfort OAuth verwenden.

## 6. Auditierbarkeit und operative Transparenz

- **Nachverfolgbare Metadaten** – Agentenschlüssel erfassen `created_at`, `last_used_at`, `bound_agent_id`, Status und Widerrufsereignisse. `state.json` spiegelt die zuletzt gesehenen Zeitstempel der Agenten für schnelle Health-Checks wider.
- **Log-Streaming** – Echtzeit-Logs werden per Redis Pub/Sub gestreamt. Sensible Werte wie Tokens und Schlüssel werden maskiert, bevor sie den Client erreichen.
- **Status-APIs** – `/api/v2/overview` fasst Tunnel-, Agenten- und Konfigurationsstatus für Monitoring-Systeme oder GitOps-Workflows zusammen.

## 7. Empfehlungen für den Betrieb

| Bereich | Empfehlung |
| --- | --- |
| Docker-Volumes | Persistieren Sie `/app/data` für verschlüsselte Konfiguration, Schlüssel und Status. Persistieren Sie `/app/logs`, wenn Datei-Logging aktiviert ist, und stellen Sie sicher, dass Host-Mounts für UID/GID 65532 oder angepasste Build-Argumente schreibbar sind. |
| Redis | Betreiben Sie `redis:7-alpine` zusammen mit DockFlare in einem privaten Netzwerk (`dockflare-internal`) oder verwenden Sie eine gehärtete Redis-Instanz mit Authentifizierung und TLS. Vermeiden Sie es, Redis öffentlich erreichbar zu machen. Nutzen Sie `REDIS_DB_INDEX`, um DockFlare-Daten von anderen Containern in derselben Redis-Instanz zu trennen. |
| Backups | Laden Sie die `.zip` regelmäßig herunter und bewahren Sie sie zusammen mit `dockflare.key` auf. Beide Dateien werden benötigt, um die Konfiguration bei einer Wiederherstellung zu entschlüsseln. |
| Agenten | Behandeln Sie API-Schlüssel wie Zugangsdaten. Betreiben Sie Agenten mit Socket-Proxy, sodass nur die benötigten Docker-Endpunkte freigegeben sind. Denken Sie daran, dass der Container als unprivilegierter Benutzer `dockflare` (UID/GID 65532) läuft; gleichen Sie Host-Berechtigungen an oder bauen Sie mit `DOCKFLARE_UID/DOCKFLARE_GID` neu. |
| Reverse Proxy | Platzieren Sie DockFlare hinter Cloudflare Access oder einem anderen vertrauenswürdigen IdP. Wenn Sie die Passwort-Anmeldung deaktivieren, muss die vorgelagerte Authentifizierung in jedem Fall zuverlässig erzwungen werden. |
| Monitoring | Alarmieren Sie bei unerwarteten Neustarts, fehlenden Agent-Heartbeats oder neu ausgestellten Schlüsseln außerhalb geplanter Wartungsfenster. |

## 8. Künftige Erweiterungen (Roadmap)

- Optionale Passphrasen-Absicherung für den Fernet-Schlüssel im Ruhezustand.
- Automatisierte Rotation von Agentenschlüsseln mit Grace-Perioden für gestaffelte Rollouts.
- Feingranulare Rechteumfänge für Agentenbefehle, um Lese- und Schreiboperationen besser zu trennen.

---

DockFlare wird mit Blick auf Sicherheit kontinuierlich weiterentwickelt. Behalten Sie die Release Notes im Blick und bringen Sie Ideen über den Issue-Tracker ein, wenn Sie zusätzliche Schutzmechanismen benötigen.
