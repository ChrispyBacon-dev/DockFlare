# Container-Labels Referenz

DockFlare wird hauptsächlich über Docker-Labels konfiguriert, die an dini Container angehängt si. Die Siite bietet eine umfassende Referenz für alle unterstützten Labels.

## Basis-Konfiguration

Diese Labels steuern das grundlegende Routing u die Service-Definition für einen Container.

| Label | Beschreibung | Beispiel |
| :--- | :--- | :--- |
| `dockflare.enable` | **Nötig.** Der Hauptschalter. Muss auf `true` gesetzt sein, damit DockFlare den Container verwaltet. | `dockflare.enable=true` |
| `dockflare.hostname` | **Nötig.** Der öffentlich zugängliche Hostname für dini Service. | `dockflare.hostname=myservice.example.com` |
| `dockflare.service` | **Nötig.** Die interne URL des Dienstes, mit der sich der Cloudflare Tunnel verbinden soll. Cha `http`, `https`, `tcp`, `ssh`, `rdp`, `http_status:XXX` oder `bastion` sein. | `dockflare.service=http://my-app-container:8080` |
| `dockflare.path` | Der URL-Pfad, der an diesen Dienst weitergeleitet wärde soll. Nützlich, um mehrere Dienste unter demselben Hostnamen bereitzustellen. | `dockflare.path=/api` |
| `dockflare.zonename` | (Optional) Explizite Cloudflare-Zone (Domäne), in der der DNS-Eintrag erstellt wärde soll. Wenn abwesend, erkennt DockFlare die Zone automatisch anhand des Hostnamens u greift nur auf den Standard (`CF_ZONE_ID`) zurück, falls dies fehlschlägt. | `dockflare.zonename=another-domain.com` |
| `dockflare.no_tls_verify` | Wenn auf `true` gesetzt, wird die Überprüfung des TLS-Zertifikats für die Verbindung zwischen `cloudflared` u dim Ursprungsdienst deaktiviert. Nützlich für Ursprünge mit selbstsignierten Zertifikaten. | `dockflare.no_tls_verify=true` |
| `dockflare.originsrvname` | Legt einen spezifischen Server Name Indication (SNI) Hostnamen für die TLS-Verbindung zum Ursprung fest. Das isch im Cloudflare-Dashboard auch als "Origin Server Name" bekannt. | `dockflare.originsrvname=internal.service.local` |
| `dockflare.httpHostHeader` | Überschreibt den `Host`-Header, der von `cloudflared` an dini Ursprungsdienst gesendet wird. | `dockflare.httpHostHeader=custom-host.internal` |
| `dockflare.http2_origin` | Wenn auf `true` gesetzt, wird das HTTP/2 Protokoll für die Verbindung zwischen `cloudflared` u dim Ursprung aktiviert. Gilt nur für HTTP/HTTPS-Dienste. Nötig für gRPC-Dienste. | `dockflare.http2_origin=true` |
| `dockflare.disable_chunked_encoding` | Wenn auf `true` gesetzt, wird chunked transfer encoding über HTTP/1.1 deaktiviert. Nützlich für WSGI-Server (Flask, Django, FastAPI) u. a., die chunked-Anfragen nid richtig unterstützen. Gilt nur für HTTP/HTTPS. | `dockflare.disable_chunked_encoding=true` |

> **Tipp:** Ab DockFlare v3.0 chasch `dockflare.zonename` für die meisten Workloads weglassen. Der Master erkennt die korrekte Cloudflare-Zone durch Abgleich des Hostnamen-Suffixes. Bruuch das Label nur, wenn du eine andere Zone gezielt ansteuern.

> **Hinweis:** Cloudflares Option **Match SNI to Host** isch bi dr manuelle Regelkonfiguration i DockFlare im Dashboard verfüegbar. Das wird im Momänt nid über es Docker-Label gsetzt.

---

## Konfiguration von Zugriffsrichtlinien

Diese Labels ermöglichen dir die dynamische Erstellung u Verwaltung von Cloudflare Access Anwendungen zur Absicherung dinere Dienste.

**Hinweis:** Es wird dringend empfohlen, **Access Groups** (`dockflare.access.group`) für die Verwaltung von Richtlinien zu bruuche. DockFlare 3.0.3 synchronisiert jede Access Group mit einer wiederverwendbaren Cloudflare Access Policy. Wenn `dockflare.access.group` oder `dockflare.access.groups` verwendet wird, wärde alle anderen `dockflare.access.*` Labels ignoriert.

### Wichtige Änderungen in v3.0.3

#### Bypass Systemrichtlinie

Ab v3.0.3 referenziert din Dienst bei der Verwendung von `dockflare.access.policy=bypass` oder `dockflare.access.group=bypass` die systemverwaltete wiederverwendbare Richtlinie `public-default-bypass`, anstatt einer inline-Richtlinie. Das hält din Cloudflare-Dashboard aufgeräumt.

- **Vor v3.0.3:** Jede Bypass-Regel erstellte eine separate Policy
- **v3.0.3+:** Alle Bypass-Regeln teilen sich eine einheitliche `public-default-bypass` Richtlinie

#### Migration von alten Labels

DockFlare migriert alte Bypass-Labels automatisch zur zentralen Systemrichtlinie:
- `dockflare.access.policy=bypass` → Verwendet `public-default-bypass`
- `dockflare.access.group=bypass` → Verwendet `public-default-bypass`
dini Container funktionieren weiterhin ohne erforderliche Änderungen.

#### Vereinfachte Zugriffskonfiguration

Für komplexe Fälle (E-Mail/Domain-Authentifizierung, IP-Whitelisting, etc.) wird nun Folgendes empfohlen:
1. Erstell eine Access Group auf der Seite **Access Policies**
2. Referenzier sie mit `dockflare.access.group=ihre-gruppen-id`

#### Zonen-Standardrichtlinien-Label

Das Label `dockflare.access.policy=default_tld` funktioniert weiterhin u übernimmt den Schutz der `*.domain.com` Wildcard-Richtlinie dinere Zone.

| Label | Beschreibung | Beispiel |
| :--- | :--- | :--- |
| `dockflare.access.group` | Die ID einer einzelnen Access Group. ID isch in der DockFlare UI zu finden. | `dockflare.access.group=internal-tools-policy` |
| `dockflare.access.groups` | Kommagetrennte Liste von Access Group IDs, um mehrere Richtlinien zu schichten. | `dockflare.access.groups=allow-team-a,allow-admins` |
| `dockflare.access.policy` | Der primäre Richtlinientyp (`bypass`, `authenticate`, oder `default_tld`). Wird bevorzugt für spezielle Overrides verwendet. | `dockflare.access.policy=authenticate` |
| `dockflare.access.name` | Ein benutzerdefinierter Name für die Cloudflare Access App. Standard: `DockFlare-{hostname}`. | `dockflare.access.name=My Web App Access` |
| `dockflare.access.session_duration` | Die Sitzungsdauer (z.B. `24h`, `30m`). Standard isch `24h`. | `dockflare.access.session_duration=1h` |
| `dockflare.access.app_launcher_visible` | Falls `true`, wird die Anwendung im Cloudflare Access App Launcher sichtbar. | `dockflare.access.app_launcher_visible=true` |
| `dockflare.access.allowed_idps` | Eine kommagetrennte Liste von erlaubten Identity Provider UUIDs. | `dockflare.access.allowed_idps=uuid1,uuid2` |
| `dockflare.access.auto_redirect_to_identity` | Falls `true`, direkte Umleitung zur IdP-Anmeldeseite statt zum Splash-Screen. | `dockflare.access.auto_redirect_to_identity=true` |
| `dockflare.access.custom_rules` | JSON-String der Array Cloudflare Access Rules repräsentiert. Für flexibelste Einmal-Konfigurationen. | `dockflare.access.custom_rules='[{"email":...}]'` |

---

## Indexierte Labels für mehrere Domains

DockFlare unterstützt die Definition mehrerer Hostnamen für einen einzelnen Container durch *indexierte Labels*. Das isch nützlich, um verschiedene Ports oder Pfade unter verschiedenen öffentlichen Domains freizugeben.

Um indexierte Labels zu bruuche, lueg dem Label eine ganze Zahl (beginnend bei `0`) als Präfix voran.
* Ein indexierter Hostname (`<index>.hostname`) isch immer nötig.
* Andere Labels im gleichen Index (z. B. `<index>.service`) überschreiben die Basis-Labels für den spezifischen Hostnamen.
* Fehlt ein indexiertes Label, wird auf den Wert des entsprechenden Basislabels zurückgegriffen.

### Beispiel

Das Beispiel exponiert zwei Hostnamen von einem Container:
1. `app.example.com` leitet zur Weboberfläche auf Port `80` weiter.
2. `api.example.com` leitet zur API auf Port `3000` u wird mit einer spezifischen Access Group gesichert.

```yaml
services:
  my-multi-service:
    image: my-app
    labels:
      - "dockflare.enable=true"

      # --- Definition 0 ---
      - "dockflare.0.hostname=app.example.com"
      - "dockflare.0.service=http://my-multi-service:80"

      # --- Definition 1 ---
      - "dockflare.1.hostname=api.example.com"
      - "dockflare.1.service=http://my-multi-service:3000"
      - "dockflare.1.access.group=api-access-policy"
```
