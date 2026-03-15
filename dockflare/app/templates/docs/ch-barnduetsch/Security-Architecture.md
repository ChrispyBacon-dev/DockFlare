# DockFlare Sicherheitsarchitektur u Härtung

Das Dok git dir e Überblick, wie DockFlare ab Version 3.0+ Master u Agent absichert u was im Betrieb wichtig isch.

## 1. Vertrauensmodell der Control Plane

- **Dr Master isch d zentrale Vertrauensinstanz**: Cloudflare-Zugangsdaten u Richtlinie blybe dört.
- **Jede Agent-Registrierig het eigeti API-Schlüssle**: Die wärde verschlüsslet gspeicheret.
- **D Master-API isch gschützt**: Web UI u `/api/v2/*` bruuchä e Session oder dr Master-API-Key.

## 2. Verschlüsselte Konfiguration u Schlüsselverwaltung

- **`dockflare_config.dat` isch verschlüsslet**
- **`agent_keys.dat` isch o verschlüsslet**
- **Nach ere Wiederherstellig startet dr Container automatisch neu**
- **`state.json` blybt bewusst im Klartext für Sichtbarkeit, aber ohni Geheimnis**

## 3. Garantien für Backup u Wiederherstellung

- **Im Archiv si aui kritische Date drin**
- **D Wiederherstellig lädt d Artefakt wieder i u startet neu**
- **E einzelni `state.json` wird für Spezialfäll no unterstützt**

## 4. Netzwerk- u Kommunikationssicherheit

- **Agenten müesse kei iigahendi Port ufmache**
- **Agentenaufrüef si mit API-Key u Agent-ID abgsicheret**
- **Redis söll im private `dockflare-internal`-Netz blybe**
- **Master u Agent laufe mit möglichst wenig Rächt**

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
