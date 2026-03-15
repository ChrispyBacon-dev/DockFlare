# Container-Labels Referenz

DockFlare wird hauptsächlich über Docker-Labels konfiguriert, die an Ihre Container angehängt sind. Diese Seite bietet eine umfassende Referenz für alle unterstützten Labels.

## Basis-Konfiguration

Diese Labels steuern das grundlegende Routing und die Service-Definition für einen Container.

| Label | Beschreibung | Beispiel |
| :--- | :--- | :--- |
| `dockflare.enable` | **Erforderlich.** Der Hauptschalter. Muss auf `true` gesetzt sein, damit DockFlare den Container verwaltet. | `dockflare.enable=true` |
| `dockflare.hostname` | **Erforderlich.** Der öffentlich zugängliche Hostname für Ihren Service. | `dockflare.hostname=myservice.example.com` |
| `dockflare.service` | **Erforderlich.** Die interne URL des Dienstes, mit der sich der Cloudflare Tunnel verbinden soll. Kann `http`, `https`, `tcp`, `ssh`, `rdp`, `http_status:XXX` oder `bastion` sein. | `dockflare.service=http://my-app-container:8080` |
| `dockflare.path` | Der URL-Pfad, der an diesen Dienst weitergeleitet werden soll. Nützlich, um mehrere Dienste unter demselben Hostnamen bereitzustellen. | `dockflare.path=/api` |
| `dockflare.zonename` | (Optional) Explizite Cloudflare-Zone (Domäne), in der der DNS-Eintrag erstellt werden soll. Wenn abwesend, erkennt DockFlare die Zone automatisch anhand des Hostnamens und greift nur auf den Standard (`CF_ZONE_ID`) zurück, falls dies fehlschlägt. | `dockflare.zonename=another-domain.com` |
| `dockflare.no_tls_verify` | Wenn auf `true` gesetzt, wird die Überprüfung des TLS-Zertifikats für die Verbindung zwischen `cloudflared` und Ihrem Ursprungsdienst deaktiviert. Nützlich für Ursprünge mit selbstsignierten Zertifikaten. | `dockflare.no_tls_verify=true` |
| `dockflare.originsrvname` | Legt einen spezifischen Server Name Indication (SNI) Hostnamen für die TLS-Verbindung zum Ursprung fest. Dies ist im Cloudflare-Dashboard auch als "Origin Server Name" bekannt. | `dockflare.originsrvname=internal.service.local` |
| `dockflare.httpHostHeader` | Überschreibt den `Host`-Header, der von `cloudflared` an Ihren Ursprungsdienst gesendet wird. | `dockflare.httpHostHeader=custom-host.internal` |
| `dockflare.http2_origin` | Wenn auf `true` gesetzt, wird das HTTP/2 Protokoll für die Verbindung zwischen `cloudflared` und Ihrem Ursprung aktiviert. Gilt nur für HTTP/HTTPS-Dienste. Erforderlich für gRPC-Dienste. | `dockflare.http2_origin=true` |
| `dockflare.disable_chunked_encoding` | Wenn auf `true` gesetzt, wird chunked transfer encoding über HTTP/1.1 deaktiviert. Nützlich für WSGI-Server (Flask, Django, FastAPI) u. a., die chunked-Anfragen nicht richtig unterstützen. Gilt nur für HTTP/HTTPS. | `dockflare.disable_chunked_encoding=true` |

> **Tipp:** Ab DockFlare v3.0 können Sie `dockflare.zonename` für die meisten Workloads weglassen. Der Master erkennt die korrekte Cloudflare-Zone durch Abgleich des Hostnamen-Suffixes. Nutzen Sie das Label nur, wenn Sie eine andere Zone gezielt ansteuern.

> **Hinweis:** Cloudflares Option **Match SNI to Host** ist bei der manuellen Regelkonfiguration in DockFlare im Dashboard verfügbar. Sie wird derzeit nicht über ein Docker-Label festgelegt.

---

## Konfiguration von Zugriffsrichtlinien

Diese Labels ermöglichen Ihnen die dynamische Erstellung und Verwaltung von Cloudflare Access Anwendungen zur Absicherung Ihrer Dienste.

**Hinweis:** Es wird dringend empfohlen, **Access Groups** (`dockflare.access.group`) für die Verwaltung von Richtlinien zu verwenden. DockFlare 3.0.3 synchronisiert jede Access Group mit einer wiederverwendbaren Cloudflare Access Policy. Wenn `dockflare.access.group` oder `dockflare.access.groups` verwendet wird, werden alle anderen `dockflare.access.*` Labels ignoriert.

### Wichtige Änderungen in v3.0.3

#### Bypass Systemrichtlinie

Ab v3.0.3 referenziert Ihr Dienst bei der Verwendung von `dockflare.access.policy=bypass` oder `dockflare.access.group=bypass` die systemverwaltete wiederverwendbare Richtlinie `public-default-bypass`, anstatt einer inline-Richtlinie. Dies hält Ihr Cloudflare-Dashboard aufgeräumt.

- **Vor v3.0.3:** Jede Bypass-Regel erstellte eine separate Policy
- **v3.0.3+:** Alle Bypass-Regeln teilen sich eine einheitliche `public-default-bypass` Richtlinie

#### Migration von alten Labels

DockFlare migriert alte Bypass-Labels automatisch zur zentralen Systemrichtlinie:
- `dockflare.access.policy=bypass` → Verwendet `public-default-bypass`
- `dockflare.access.group=bypass` → Verwendet `public-default-bypass`
Ihre Container funktionieren weiterhin ohne erforderliche Änderungen.

#### Vereinfachte Zugriffskonfiguration

Für komplexe Fälle (E-Mail/Domain-Authentifizierung, IP-Whitelisting, etc.) wird nun Folgendes empfohlen:
1. Erstellen Sie eine Access Group auf der Seite **Access Policies**
2. Referenzieren Sie sie mit `dockflare.access.group=ihre-gruppen-id`

#### Zonen-Standardrichtlinien-Label

Das Label `dockflare.access.policy=default_tld` funktioniert weiterhin und übernimmt den Schutz der `*.domain.com` Wildcard-Richtlinie Ihrer Zone.

| Label | Beschreibung | Beispiel |
| :--- | :--- | :--- |
| `dockflare.access.group` | Die ID einer einzelnen Access Group. ID ist in der DockFlare UI zu finden. | `dockflare.access.group=internal-tools-policy` |
| `dockflare.access.groups` | Kommagetrennte Liste von Access Group IDs, um mehrere Richtlinien zu schichten. | `dockflare.access.groups=allow-team-a,allow-admins` |
| `dockflare.access.policy` | Der primäre Richtlinientyp (`bypass`, `authenticate`, oder `default_tld`). Wird bevorzugt für spezielle Overrides verwendet. | `dockflare.access.policy=authenticate` |
| `dockflare.access.name` | Ein benutzerdefinierter Name für die Cloudflare Access App. Standard: `DockFlare-{hostname}`. | `dockflare.access.name=My Web App Access` |
| `dockflare.access.session_duration` | Die Sitzungsdauer (z.B. `24h`, `30m`). Standard ist `24h`. | `dockflare.access.session_duration=1h` |
| `dockflare.access.app_launcher_visible` | Falls `true`, wird die Anwendung im Cloudflare Access App Launcher sichtbar. | `dockflare.access.app_launcher_visible=true` |
| `dockflare.access.allowed_idps` | Eine kommagetrennte Liste von erlaubten Identity Provider UUIDs. | `dockflare.access.allowed_idps=uuid1,uuid2` |
| `dockflare.access.auto_redirect_to_identity` | Falls `true`, direkte Umleitung zur IdP-Anmeldeseite statt zum Splash-Screen. | `dockflare.access.auto_redirect_to_identity=true` |
| `dockflare.access.custom_rules` | JSON-String der Array Cloudflare Access Rules repräsentiert. Für flexibelste Einmal-Konfigurationen. | `dockflare.access.custom_rules='[{"email":...}]'` |

---

## Indexierte Labels für mehrere Domains

DockFlare unterstützt die Definition mehrerer Hostnamen für einen einzelnen Container durch *indexierte Labels*. Das ist nützlich, um verschiedene Ports oder Pfade unter verschiedenen öffentlichen Domains freizugeben.

Um indexierte Labels zu verwenden, stellen Sie dem Label eine ganze Zahl (beginnend bei `0`) als Präfix voran.
* Ein indexierter Hostname (`<index>.hostname`) ist immer erforderlich.
* Andere Labels im gleichen Index (z. B. `<index>.service`) überschreiben die Basis-Labels für den spezifischen Hostnamen.
* Fehlt ein indexiertes Label, wird auf den Wert des entsprechenden Basislabels zurückgegriffen.

### Beispiel

Dieses Beispiel exponiert zwei Hostnamen von einem Container:
1. `app.example.com` leitet zur Weboberfläche auf Port `80` weiter.
2. `api.example.com` leitet zur API auf Port `3000` und wird mit einer spezifischen Access Group gesichert.

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
