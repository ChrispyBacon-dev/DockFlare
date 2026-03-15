# DockFlare Sicherheitsarchitektur u Härtung

Das Dok erläutert, wie DockFlare in Version 3.0+ sowohl den Master-Knoten als auch registrierte Agenten absichert. Es ergänzt das Sicherheitsaudit, indem es die in DockFlare integrierten Schutzmechanismen u empfohlene Betriebspraktiken zusammenfasst.

## 1. Vertrauensmodell der Control Plane

- **Master als massgebliche Instanz** – Der DockFlare Master verwaltet alle Cloudflare-Zugangsdaten u Richtliniendefinitionen. Agenten verwalten kener API-Tokens selbst, sondern führen Anweisungen aus, die sie über einen authentifizierten Kanal erhalten.
- **API-Schlüssel pro Agent** – Für die Registrierung isch ein eindeutiger API-Schlüssel nötig, der vom Master ausgestellt wird. Die Schlüssel wärde zusammen mit Metadaten wie Eigentümer, Zeitstempeln u Status verschlüsselt in `agent_keys.dat` gespeichert, sodass sie jederzeit rotiert oder widerrufen wärde chöi.
- **Schutz der Master-API** – Administrative Endpunkte, darunter die Web UI u `/api/v2/*`, erfordern entweder eine gültige Sitzung oder den Master-API-Schlüssel. Tokens wärde in Antworten u Logs maskiert u chöi ohne Neustart des Stacks rotiert wärde.

## 2. Verschlüsselte Konfiguration u Schlüsselverwaltung

- **Verschlüsseltes `dockflare_config.dat`** – Cloudflare-Zugangsdaten, UI-Konten, Tunnel-Standardeinstellungen u der Master-Schlüssel wärde in einem verschlüsselten Blob gespeichert, der durch `dockflare.key` geschützt isch.
- **Verschlüsseltes Agentenregister** – API-Schlüssel der Agenten u ihre Audit-Metadaten liegen in `agent_keys.dat`, verschlüsselt mit demselben Fernet-Schlüssel. Sensible Daten erscheinen nid mehr im Klartext in `state.json`.
- **Automatischer Neustart nach Wiederherstellung** – Wenn ein Backup wiederhergestellt wird, schreibt DockFlare die verschlüsselten Artefakte, lädt den Laufzeitstatus neu, setzt ein Neustart-Flag u beendet sich. Die Docker-Restart-Policy startet den Container nachhär sofort mit der neuen Konfiguration neu.
- **Klartext-`state.json` für Beobachtbarkeit** – `state.json` bleibt bewusst im Klartext, damit Operatoren Regeln u Agenten prüfen chöi. Für Geheimnisse bleiben die verschlüsselten Dateien massgeblich.

## 3. Garantien für Backup u Wiederherstellung

- **Inhalt des Archivs** – Jedes Backup-Archiv (`dockflare_backup_*.zip`) enthält `dockflare_config.dat`, `dockflare.key`, `agent_keys.dat`, `state.json` sowie ein `manifest.json` mit Prüfsummen u Versionsmetadaten. Zum Wiederaufbau eines Master-Knotens si kener weiteren Dateien nötig.
- **Automatisierter Wiederherstellungsablauf** – Eine Wiederherstellung über den Einrichtungsassistenten oder die Einstellungsseite schreibt die Artefakte, lädt Laufzeit-Caches neu u erzwingt einen Container-Neustart, damit die verschlüsselte Konfiguration sofort aktiv wird.
- **Abwärtskompatibilität** – Das Hochladen einer einzelnen `state.json` wird weiterhin für Troubleshooting oder Teilmigrationen unterstützt. DockFlare importiert dabei den Laufzeitstatus, behält aber die vorhandene verschlüsselte Konfiguration bei, um versehentliche Zurücksetzungen von Zugangsdaten zu vermeiden.

## 4. Netzwerk- u Kommunikationssicherheit

- **Cloudflare-Tunnel als Transportweg** – Agenten ufmache kener eingehenden Ports. Der gesamte Verkehr läuft über den vom Master verwalteten Cloudflare-Tunnel, wodurch sich die Angriffsfläche auf entfernten Hosts verringert.
- **Authentifizierte Agentenaufrufe** – REST-Aufrufe der Agenten enthalten ihren API-Schlüssel u si an die registrierte Agent-ID gebunden. Token-Abweichungen oder widerrufene Schlüssel wärde abgewiesen.
- **Redis-Backplane** – DockFlare verwendet Redis für Caching, Log-Streaming u Signalisierung zwischen Threads. Der empfohlene Compose-Stack hält Redis in einem eigenen `dockflare-internal`-Netzwerk, sodass Workloads im `cloudflare-net` nid direkt darauf zugreifen chöi. Externes Redis sollte mit Authentifizierung u TLS abgesichert wärde.
- **Least-Privilege-Laufzeit** – Sowohl der Master als auch die Agenten laufen als Benutzer `dockflare` (UID/GID 65532) u kommunizieren mit Docker ausschliesslich über den mitgelieferten Socket-Proxy, wodurch die freigegebene API-Oberfläche klein bleibt.

## 5. Authentifizierung u Autorisierung

- **Abgesicherter UI-Login** – Der Assistent für die Ersteinrichtung erzwingt die Erstellung eines Administratorkontos für die UI. Die Passwort-Anmeldung cha deaktiviert wärde, **dies wird jedoch wegen der Sicherheitsrisiken im Docker-Netzwerk dringend nid empfohlen**.
- **Sitzungsverwaltung** – Flask-Login-Sitzungen si an die verschlüsselte Konfiguration gebunden. Beim Wiederherstellen eines Backups oder bei einer Rotation von Zugangsdaten wärde bestehende Sitzungen automatisch ungültig.
- **Agenten-ACLs** – Jeder Agenteneintrag verfolgt Tunnel-Zuordnung, Heartbeat-Zeitstempel u ausstehende Befehle. Der Master liefert Befehle nur an Agenten aus, die den korrekten Token u einen gueltigen Registrierungsstatus vorweisen.

### ⚠️ Wichtiger Sicherheitshinweis zu „Passwort-Anmeldung deaktivieren“

DockFlare enthält die Istellige „Passwort-Anmeldung deaktivieren“ für fortgschrittni Bereitstellungen, bei denen DockFlare selbst durch eine externe Authentifizierungsschicht wie Cloudflare Access geschützt isch. **Für die meisten Bereitstellungen raten wir ausdrücklich davon ab.**

**Sicherheitsrisiken bei aktivierter Option:**
- **Alle API-Endpunkte si ohne Authentifizierung erreichbar**, wenn diese Istellige aktiviert isch.
- **Sichtbarkeit im Docker-Netzwerk:** Selbst wenn DockFlare im öffentlichen Internet durch Cloudflare Access geschützt isch, chöi Container im selben Docker-Netzwerk die externe Authentifizierung umgehen u direkt auf die DockFlare-API zugreifen.
- **Keine Durchsetzung der Authentifizierung:** Die Anwendung geht davon aus, dass die externe Authentifizierung die Sicherheit übernimmt.

**Beispiel für einen Angriffsweg:**
```
Internet → Cloudflare Access (Protected) → DockFlare ✅
         ↓
Docker Network → Other Container → DockFlare API (Unprotected) ❌
```

**Empfohlene Vorgehensweise:**
Statt d'Passwort-Authentifizierung z'deaktiviere, nimmsch e vo dene sichere Optionä:
1. **Lokale DockFlare-Zugangsdaten** - Einfache, in DockFlare integrierte Passwort-Authentifizierung
2. **OAuth/OIDC-Anbieter** - Konfigurier Google, GitHub, Azure AD oder andere Identitätsanbieter für komfortables Single Sign-On ohne Sicherheitsverlust

Beidi Optionä gits der e sauberi Authentifizierig u trotz däm dr Komfort vo SSO. Mit OAuth hesch Single Sign-On, ohni d'Sicherheitsrisike vo ere deaktivierte Aameldig in Chouf z'näh.

**Fazit:** Wänn du nid grad e sehr spezifischi u richtig guet verstandeni Sicherheitsarchitektur mit sauberer Netzwerkisolierig hesch, söttsch d'Passwort-Aameldig aktiviert lah u für meh Komfort OAuth bruuche.

## 6. Auditierbarkeit u operative Transparenz

- **Nachverfolgbare Metadaten** – Agentenschlüssel erfassen `created_at`, `last_used_at`, `bound_agent_id`, Status u Widerrufsereignisse. `state.json` spiegelt die zuletzt gesehenen Zeitstempel der Agenten für schnelle Health-Checks wider.
- **Log-Streaming** – Echtzeit-Logs wärde per Redis Pub/Sub gestreamt. Sensible Werte wie Tokens u Schlüssel wärde maskiert, bevor sie den Client erreichen.
- **Status-APIs** – `/api/v2/overview` fasst Tunnel-, Agenten- u Konfigurationsstatus für Monitoring-Systeme oder GitOps-Workflows zusammen.

## 7. Empfehlungen für den Betrieb

| Bereich | Empfehlung |
| --- | --- |
| Docker-Volumes | Persistier `/app/data` für verschlüsselte Konfiguration, Schlüssel u Status. Persistier `/app/logs`, wenn Datei-Logging aktiviert isch, u lueg dass Host-Mounts für UID/GID 65532 oder angepasste Build-Argumente schreibbar si. |
| Redis | Betriib `redis:7-alpine` zäme mit DockFlare i mene private Netzwerk (`dockflare-internal`) oder nimm e ghärteti Redis-Instanz mit Authentifizierig u TLS. Vermeid es, Redis öffentlich erreichbar z'mache. Bruuch `REDIS_DB_INDEX`, um DockFlare-Date vo andere Containern i dr gliche Redis-Instanz z'trenne. |
| Backups | Lad die `.zip` regelmässig herunter u bhalt sie zusammen mit `dockflare.key` auf. Beide Dateien wärde benötigt, um die Konfiguration bei einer Wiederherstellung zu entschlüsseln. |
| Agenten | Behandle API-Schlüssel wie Zugangsdaten. Betriib Agenten mit Socket-Proxy, sodass nur die benötigten Docker-Endpunkte freigegeben si. Denk dran: dr Container lauft als unprivilegierte Benutzer `dockflare` (UID/GID 65532); glich d'Host-Berechtige a oder bau s'Image mit `DOCKFLARE_UID/DOCKFLARE_GID` neu. |
| Reverse Proxy | Stell DockFlare hinger Cloudflare Access oder eme angere vertrouenswürdige IdP. Wänn du d'Passwort-Aameldig deaktiviersch, mues d'vorglagereti Authentifizierig i jedem Fall zuverlässig erzwunge wärde. |
| Monitoring | Alarmier bei unerwarteten Neustarts, fehlenden Agent-Heartbeats oder neu ausgestellten Schlüsseln ausserhalb geplanter Wartungsfenster. |

## 8. Künftige Erweiterungen (Roadmap)

- Optionale Passphrasen-Absicherung für den Fernet-Schlüssel im Ruhezustand.
- Automatisierte Rotation von Agentenschlüsseln mit Grace-Perioden für gestaffelte Rollouts.
- Feingranulare Rechteumfänge für Agentenbefehle, um Lese- u Schreiboperationen besser zu trennen.

---

DockFlare wird mit Blick uf Sicherheit laufend witerentwicklet. Bhalt d'Release Notes im Blick u bring Idee über dr Issue-Tracker iih, wänn du no meh Schutzmechanisme bruuche chasch.
