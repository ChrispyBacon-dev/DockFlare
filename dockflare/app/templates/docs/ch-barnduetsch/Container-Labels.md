# Container-Labels-Referänz

DockFlare wird vor allem über Docker-Labels konfiguriert, wo du direkt a dini Container hängsch. Die Syte isch d Referänz für aui unterstützte Labels.

## Basis-Konfiguration

Die Labels steuere ds grundlegende Routing u d Service-Definition für e Container.

| Label | Beschrybig | Bispiel |
| :--- | :--- | :--- |
| `dockflare.enable` | **Pflicht.** Dr Hauptschalter. Muess uf `true` gsetzt sy, damit DockFlare dr Container verwaltet. | `dockflare.enable=true` |
| `dockflare.hostname` | **Pflicht.** Dr öffentlechi Hostname für dyn Dienst. | `dockflare.hostname=myservice.example.com` |
| `dockflare.service` | **Pflicht.** D interni URL vom Dienst, wo sech dr Cloudflare Tunnel drmit verbindet. Cha `http`, `https`, `tcp`, `ssh`, `rdp`, `http_status:XXX` oder `bastion` sy. | `dockflare.service=http://my-app-container:8080` |
| `dockflare.path` | URL-Pfad, wo a dä Dienst wytergleitet wird. Praktisch, wänn mehri Dienscht under em glyche Hostname loufe. | `dockflare.path=/api` |
| `dockflare.zonename` | (Optional) Expliziti Cloudflare-Zone, wo dr DNS-Iitrag drin erstellt wird. Wänn s Label fählt, erkennt DockFlare d Zone normalerwys automatisch us em Hostname. | `dockflare.zonename=another-domain.com` |
| `dockflare.no_tls_verify` | Wänn uf `true` gsetzt, wird d TLS-Zertifikatsprüefig für d Verbindig zwüsche `cloudflared` u dim Ursprung deaktiviert. Sinnvoll bi sälbstsignierte Zertifikat. | `dockflare.no_tls_verify=true` |
| `dockflare.originsrvname` | Definiert e spezifische SNI-Hostname für d TLS-Verbindig zum Ursprung. Das isch im Cloudflare-Dashboard o als **Origin Server Name** bekannt. | `dockflare.originsrvname=internal.service.local` |
| `dockflare.httpHostHeader` | Überschrybt dr `Host`-Header, wo `cloudflared` a dr Ursprung schickt. | `dockflare.httpHostHeader=custom-host.internal` |
| `dockflare.http2_origin` | Wänn uf `true` gsetzt, wird HTTP/2 für d Verbindig zwüsche `cloudflared` u dim Ursprung aktiviert. Gilt nume für HTTP/HTTPS-Dienscht. Nötig für gRPC. | `dockflare.http2_origin=true` |
| `dockflare.disable_chunked_encoding` | Wänn uf `true` gsetzt, wird chunked transfer encoding über HTTP/1.1 deaktiviert. Nützlich für WSGI-Server u angeri Ursprüng, wo chunked Requests nid guet unterstütze. | `dockflare.disable_chunked_encoding=true` |

> **Tipp:** Ab DockFlare v3.0 chasch `dockflare.zonename` für d meischte Workloads wägla. Dr Master erkennt d korrekti Cloudflare-Zone normalerwys automatisch über ds Hostname-Suffix.

> **Hinwys:** Cloudflares Option **Match SNI to Host** isch im DockFlare-Dashboard bi dr manuelle Regle-Konfiguration verfügbar. Über es Docker-Label cha mer das im Momänt nid setze.

---

## Labels für Zuegriffsrichtlinie

Mit dene Labels chasch Cloudflare Access Apps u Richtlinie dynamsch steuere.

**Hinwys:** Es wird dringend empfohle, **Access Groups** (`dockflare.access.group`) z bruuchen. Wänn `dockflare.access.group` oder `dockflare.access.groups` gsetzt isch, wärde aui andere `dockflare.access.*`-Labels ignoriert.

### Wichtigi Änderige ab v3.0.3

#### Bypass-Systemrichtlinie

Ab v3.0.3 verweist `dockflare.access.policy=bypass` oder `dockflare.access.group=bypass` uf d systemverwalteti Richtlinie `public-default-bypass` statt uf e inline-Richtlinie. So blybt ds Cloudflare-Dashboard ordentlecher.

* **Vor v3.0.3:** Jedi Bypass-Regle het e eigeti Policy erstellt
* **Ab v3.0.3:** Aui Bypass-Regle teile sech `public-default-bypass`

#### Migration vo alte Labels

Alti Bypass-Labels wärde automatisch uf d zentrali Systemrichtlinie umgstellt:

* `dockflare.access.policy=bypass` → `public-default-bypass`
* `dockflare.access.group=bypass` → `public-default-bypass`

Dini Container loufe wyter ohni nötigi Änderige.

#### Vereinfachti Zugriffskonfiguration

Für komplexeri Fäll wie Mail-/Domain-Authentifizierig oder IP-Whitelisting isch d empfohlni Vorgah:

1. E Access Group uf dr Syte **Access Policies** erstelle
2. Si mit `dockflare.access.group=<gruppen-id>` referenziere

#### Zonen-Standardrichtlinie-Label

S Label `dockflare.access.policy=default_tld` funktioniert wyterhi u übernimmt dr Schutz vo dr `*.domain.com`-Wildcard-Richtlinie dimere Zone.

| Label | Beschrybig | Bispiel |
| :--- | :--- | :--- |
| `dockflare.access.group` | D ID vo ere einzelne Access Group. D ID findsch i dr DockFlare UI. | `dockflare.access.group=internal-tools-policy` |
| `dockflare.access.groups` | Kommagtrennti Lischt vo Access-Group-IDs, zum mehri Richtlinie z schichte. | `dockflare.access.groups=allow-team-a,allow-admins` |
| `dockflare.access.policy` | Dr primäri Richtlinientyp (`bypass`, `authenticate` oder `default_tld`). Vor allem für spezielli Overrides. | `dockflare.access.policy=authenticate` |
| `dockflare.access.name` | Benutzerdefinierte Name für d Cloudflare Access App. Standard: `DockFlare-{hostname}` | `dockflare.access.name=My Web App Access` |
| `dockflare.access.session_duration` | D Sitzigsduur, zum Bispiel `24h` oder `30m`. Standard isch `24h`. | `dockflare.access.session_duration=1h` |
| `dockflare.access.app_launcher_visible` | Wänn `true`, wird d Aawändig im Cloudflare Access App Launcher sichtbar. | `dockflare.access.app_launcher_visible=true` |
| `dockflare.access.allowed_idps` | Kommagtrennti Lischt mit erlaubte Identity-Provider-UUIDs. | `dockflare.access.allowed_idps=uuid1,uuid2` |
| `dockflare.access.auto_redirect_to_identity` | Wänn `true`, geit dr Traffic diräkt zur IdP-Aamäldesyte statt uf dr Splash-Screen. | `dockflare.access.auto_redirect_to_identity=true` |
| `dockflare.access.custom_rules` | JSON-String mit ere Array-Defintion vo Cloudflare Access Rules. Für maximal flexibel Einmal-Konfiguratione. | `dockflare.access.custom_rules='[{\"email\":...}]'` |

---

## Indexierti Labels für mehri Domains

DockFlare unterstützt mehri Hostname für e einzelne Container über *indexierti Labels*. Das isch nützlich, wänn verschideni Ports oder Pfäd under verschidene öffentleche Domains freigeh wötsch.

Zum indexierti Labels z bruuchen, stellsch du em Label e Ganzzahl ab `0` vorane.

* E indexierte Hostname (`<index>.hostname`) isch immer nötig.
* Anderi Labels im glyche Index (z. B. `<index>.service`) überschrybe d Basis-Labels für genau dä Hostname.
* Fählt es indexierts Label, wird dr Wert vom entsprechende Basis-Label bruucht.

### Bispiel

Ds Bispiel git zwei Hostname us em glyche Container frei:

1. `app.example.com` leitet uf d Weboberflächi uf Port `80`
2. `api.example.com` leitet uf d API uf Port `3000` u wird mit ere eigete Access Group gschützt

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
