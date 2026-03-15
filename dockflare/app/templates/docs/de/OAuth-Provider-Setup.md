## Einrichtung eines OAuth-Anbieters

> **📌 Wichtig:** Dieser Leitfaden beschreibt die Konfiguration der **DockFlare Web-UI-Authentifizierung**. Wenn Sie OAuth/OIDC für **Cloudflare Access Policies** einrichten möchten, um Ihre Dienste zu schützen, lesen Sie stattdessen [Identitätsanbieter](Identity-Providers.md).

DockFlare ermöglicht es, die Benutzerauthentifizierung über den OpenID-Connect-Standard (OIDC) an externe Anbieter auszulagern. Dadurch lässt sich Single Sign-On (SSO) für die DockFlare-Weboberfläche einrichten und mit Identitätsanbietern wie Google, Authentik, Okta und anderen integrieren.

### Einen neuen Anbieter hinzufügen

Gehen Sie folgendermaßen vor, um einen neuen OIDC-Anbieter hinzuzufügen:

1. **Zu den Einstellungen wechseln:** Öffnen Sie im Haupt-Dashboard die Seite **Settings**.
2. **OAuth-Bereich finden:** Scrollen Sie nach unten zum Abschnitt **OAuth Authentication**.
3. **Anbieter hinzufügen:** Klicken Sie auf **Add Provider**, um den Konfigurationsdialog zu öffnen.

Dabei werden Ihnen folgende Felder angezeigt:

* **Provider Type:** Dieses Feld ist auf `OpenID Connect (OIDC)` gesetzt, den modernen Standard für föderierte Authentifizierung.
* **Issuer URL:** Dies ist das wichtigste Feld. Es enthält die Basis-URL Ihres OIDC-Anbieters, die DockFlare verwendet, um die Anbieter-Konfiguration automatisch zu erkennen. Beispiele: `https://accounts.google.com` oder `https://authentik.yourdomain.com/application/o/dockflare/`.
* **Provider ID:** Ein kurzer, eindeutiger Name in Kleinbuchstaben für diesen Anbieter, zum Beispiel `google` oder `authentik-corp`. Diese ID wird intern sowie in der Callback-URL verwendet.
* **Display Name:** Der benutzerfreundliche Name, der auf der Anmeldeschaltfläche erscheint, zum Beispiel `Google` oder `Corporate SSO`.
* **Client ID:** Die öffentliche Kennung der DockFlare-Anwendung. Sie erhalten sie in der Entwicklerkonsole Ihres OIDC-Anbieters.
* **Client Secret:** Das vertrauliche Geheimnis der DockFlare-Anwendung, ebenfalls aus der Konsole Ihres OIDC-Anbieters.
* **Enable Provider:** Mit dieser Checkbox können Sie den Anbieter jederzeit aktivieren oder deaktivieren.

Nachdem Sie alle Angaben eingetragen haben, klicken Sie auf **Add Provider**, um zu speichern.

### Die Callback-URL finden

Sobald ein Anbieter hinzugefügt wurde, wird die benötigte **Callback URL** unter dem Eintrag dieses Anbieters auf der Einstellungsseite angezeigt. Sie wird auch als „Authorized redirect URI“ bezeichnet.

Sie müssen diese URL exakt kopieren und in der Administrationskonsole Ihres Anbieters zur Liste der erlaubten Callback-URLs hinzufügen.

---

### Beispiel: Google einrichten

Hier ist eine kurze Anleitung zur Einrichtung von Google als OAuth-Anbieter.

1. **Google Cloud Console öffnen:** Rufen Sie die Seite [APIs & Services > Credentials](https://console.cloud.google.com/apis/credentials) auf.
2. **Anmeldedaten erstellen:** Klicken Sie auf **+ CREATE CREDENTIALS** und wählen Sie **OAuth client ID**.
3. **Anwendung konfigurieren:**
   * Setzen Sie **Application type** auf **Web application**.
   * Vergeben Sie einen Namen, zum Beispiel `DockFlare`.
4. **Redirect URI hinzufügen:**
   * Klicken Sie unter **Authorized redirect URIs** auf **+ ADD URI**.
   * Tragen Sie die Callback-URL ein, die DockFlare anzeigt. Sie sieht etwa so aus: `https://your-dockflare-domain.com/auth/google/callback`.
5. **Erstellen und kopieren:** Klicken Sie auf **CREATE**. Es erscheint ein Fenster mit Ihrer **Client ID** und Ihrem **Client Secret**. Kopieren Sie beide Werte.
6. **In DockFlare konfigurieren:**
   * **Issuer URL:** `https://accounts.google.com`
   * **Provider ID:** `google`
   * **Display Name:** `Google`
   * **Client ID:** `(Your Client ID from Google)`
   * **Client Secret:** `(Your Client Secret from Google)`

Speichern Sie den Anbieter in DockFlare. Danach können Sie sich mit Ihrem Google-Konto anmelden.

---

### DockFlare mit OAuth und Access Policies konfigurieren

Wenn Sie OAuth-Authentifizierung verwenden, möchten Sie möglicherweise die Hauptoberfläche von DockFlare über Access Policies schützen und gleichzeitig sicherstellen, dass OAuth-Callbacks korrekt funktionieren. Das ist besonders wichtig, wenn Ihre DockFlare-Instanz zusätzlich durch IP-Beschränkungen oder andere Zugriffskontrollen geschützt ist.

#### **Best Practice: Bypass Policy für OAuth-Callbacks**

Verwenden Sie indexierte Labels, um getrennte Regeln für die Hauptoberfläche und für OAuth-Callback-Pfade anzulegen:

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

#### **Warum diese Konfiguration notwendig ist**

- **Schutz der Hauptoberfläche:** Ihr DockFlare-Dashboard bleibt durch die gewählte Access Policy geschützt
- **Funktionierendes OAuth:** OAuth-Callbacks können DockFlare ohne zusätzliche Authentifizierungsbarrieren erreichen
- **Sicherheit:** Nur die definierten Callback-Pfade werden per Bypass behandelt, nicht die gesamte Anwendung
- **Flexibilität:** Funktioniert mit jeder Kombination aus Access Policies, etwa IP-basiert oder authentifizierungsbasiert

#### **Wichtige Hinweise**

1. **Exakte Pfad-Übereinstimmung:** Der Callback-Pfad muss exakt dem entsprechen, was Ihr OAuth-Anbieter erwartet
2. **Mehrere Anbieter:** Für jeden konfigurierten OAuth-Anbieter sollten Sie eine eigene indexierte Regel anlegen
3. **Keine Wildcards:** Verwenden Sie aus Sicherheitsgründen keine generischen Wildcard-Pfade, sondern präzise Callback-URLs
4. **Testen:** Prüfen Sie nach der Konfiguration sowohl den geschützten Zugriff auf die Hauptoberfläche als auch den OAuth-Login-Flow
