## Einrichtung eines OAuth-Anbieters

> **📌 Wichtig:** Dieser Leitfaden beschreibt die Konfiguration der **DockFlare Web UI-Authentifizierung**. Wänn du OAuth/OIDC für **Cloudflare Access Policies** einrichten wotsch, um dini Dienste zu schützen, läs stattdessen [Identitätsanbieter](Identity-Providers.md).

DockFlare ermöglicht es, die Benutzerauthentifizierung über den OpenID-Connect-Standard (OIDC) an externe Anbieter auszulagern. Dadurch lässt sich Single Sign-On (SSO) für die DockFlare-Weboberfläche einrichten u mit Identitätsanbietern wie Google, Authentik, Okta u anderen integrieren.

### Einen neuen Anbieter hinzufügen

Gang folgendermassen vor, um einen neuen OIDC-Anbieter hinzuzufügen:

1. **Zu den Istellige wechseln:** Mach uf im Haupt-Dashboard die Seite **Settings**.
2. **OAuth-Bereich finden:** Scroll nach unten zum Abschnitt **OAuth Authentication**.
3. **Anbieter hinzufügen:** Klick auf **Add Provider**, um den Konfigurationsdialog zu ufmache.

Dabei wärde dir folgende Felder angezeigt:

* **Provider Type:** Das Feld isch auf `OpenID Connect (OIDC)` gesetzt, den modernen Standard für föderierte Authentifizierung.
* **Issuer URL:** Das isch das wichtigste Feld. Es enthält die Basis-URL din OIDC-Anbieters, die DockFlare verwendet, um die Anbieter-Konfiguration automatisch zu erkennen. Beispiele: `https://accounts.google.com` oder `https://authentik.yourdomain.com/application/o/dockflare/`.
* **Provider ID:** Ein kurzer, eindeutiger Name in Kleinbuchstaben für diesen Anbieter, zum Biispil `google` oder `authentik-corp`. Diese ID wird intern sowie in der Callback-URL verwendet.
* **Display Name:** Der benutzerfreundliche Name, der auf der Anmeldeschaltfläche erscheint, zum Biispil `Google` oder `Corporate SSO`.
* **Client ID:** Die öffentliche Kennung der DockFlare-Anwendung. Du bechunsch sie in der Entwicklerkonsole din OIDC-Anbieters.
* **Client Secret:** Das vertrauliche Geheimnis der DockFlare-Anwendung, ebenfalls aus der Konsole din OIDC-Anbieters.
* **Enable Provider:** Mit dieser Checkbox chasch den Anbieter jederzeit aktivieren oder deaktivieren.

Wänn du aues iitreit hesch, klick uf **Add Provider**, zum späichere.

### Die Callback-URL finden

Sobald en Aabieter drin isch, wird d'**Callback URL** under em Iitrag vo däm Aabieter uf dr Istelligs-Siite aazeigt. Si wird au als „Authorized redirect URI“ bezeichnet.

Du muesch diese URL exakt kopieren u in der Administrationskonsole din Anbieters zur Liste der erlaubten Callback-URLs hinzufügen.

---

### Beispiel: Google einrichten

Hier isch eine kurze Aaleitig zur Einrichtung von Google als OAuth-Anbieter.

1. **Google Cloud Console ufmache:** Rüef die Seite [APIs & Services > Credentials](https://console.cloud.google.com/apis/credentials) auf.
2. **Anmeldedaten erstellen:** Klick auf **+ CREATE CREDENTIALS** u wähl **OAuth client ID**.
3. **Anwendung konfigurieren:**
   * Setz **Application type** auf **Web application**.
   * Gib einen Namen, zum Biispil `DockFlare`.
4. **Redirect URI hinzufügen:**
   * Klick unter **Authorized redirect URIs** auf **+ ADD URI**.
   * Trag d'Callback-URL iih, wo DockFlare aazeigt. Das gseht öppe so us: `https://your-dockflare-domain.com/auth/google/callback`.
5. **Erstellen u kopieren:** Klick auf **CREATE**. Es erscheint ein Fenster mit dinere **Client ID** u dim **Client Secret**. Kopier beide Werte.
6. **In DockFlare konfigurieren:**
   * **Issuer URL:** `https://accounts.google.com`
   * **Provider ID:** `google`
   * **Display Name:** `Google`
   * **Client ID:** `(Your Client ID from Google)`
   * **Client Secret:** `(Your Client Secret from Google)`

Späicher dä Aabieter i DockFlare. Nachhär chasch di mit dim Google-Konto aamelde.

---

### DockFlare mit OAuth u Access Policies konfigurieren

Wänn du OAuth-Authentifizierung bruuche, wotsch du möglicherweise die Hauptoberfläche von DockFlare über Access Policies schützen u gleichzeitig sicherstellen, dass OAuth-Callbacks korrekt funktionieren. Das isch besonders wichtig, wenn dini DockFlare-Instanz zusätzlich durch IP-Beschränkungen oder andere Zugriffskontrollen geschützt isch.

#### **Best Practice: Bypass Policy für OAuth-Callbacks**

Bruuch indexierte Labels, um getrennte Regeln für die Hauptoberfläche u für OAuth-Callback-Pfade anzulegen:

```yaml
services:
  dockflare:
    image: alplat/dockflare:stable
    labels:
      # Main DockFlare interface with access policy
      - "dockflare.enable=true"
      - "dockflare.hostname=dockflare.example.com"
      - "dockflare.service=http://dockflare:5000"
      - "dockflare.access.group=team"  # your custom access policy

      # OAuth callback paths with bypass policy (required for OAuth to work)
      - "dockflare.0.hostname=dockflare.example.com"
      - "dockflare.0.path=/auth/google/callback"
      - "dockflare.0.service=http://dockflare:5000"
      - "dockflare.0.access.policy=bypass"

      # Add additional callback paths for other providers if needed
      - "dockflare.1.hostname=dockflare.example.com"
      - "dockflare.1.path=/auth/github/callback"
      - "dockflare.1.service=http://dockflare:5000"
      - "dockflare.1.access.policy=bypass"
```

#### **Warum diese Konfiguration notwendig isch**

- **Schutz der Hauptoberfläche:** din DockFlare-Dashboard bleibt durch die gewählte Access Policy geschützt
- **Funktionierendes OAuth:** OAuth-Callbacks chöi DockFlare ohne zusätzliche Authentifizierungsbarrieren erreichen
- **Sicherheit:** Nur die definierten Callback-Pfade wärde per Bypass behandelt, nid die gesamte Anwendung
- **Flexibilität:** Funktioniert mit jeder Kombination aus Access Policies, etwa IP-basiert oder authentifizierungsbasiert

#### **Wichtige Hinweise**

1. **Exakte Pfad-Übereinstimmung:** Der Callback-Pfad mues exakt dem entsprechen, was din OAuth-Anbieter erwartet
2. **Mehrere Anbieter:** Für jeden konfigurierten OAuth-Anbieter söttsch eine eigene indexierte Regel anlegen
3. **Keine Wildcards:** Bruuch aus Sicherheitsgründen kener generischen Wildcard-Pfade, sondern präzise Callback-URLs
4. **Testen:** Prüef nach der Konfiguration sowohl den geschützten Zugriff auf die Hauptoberfläche als auch den OAuth-Login-Flow
