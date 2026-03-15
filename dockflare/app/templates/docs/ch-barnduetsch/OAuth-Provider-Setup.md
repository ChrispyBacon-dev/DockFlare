## OAuth-Provider iirichte

> **📌 Wichtig:** Da geit s um d **DockFlare Web UI-Aamäldig**. Wänn du OAuth/OIDC für **Cloudflare Access Policies** iirichte wotsch, zum dini Dienscht z schütze, lueg besser [Identitätsanbieter](Identity-Providers.md) aa.

DockFlare cha d Benutzer-Aamäldig über OIDC a externi Aabieter uslagere. So chasch SSO für d DockFlare-Weboberflächi iirichte, zum Bispil mit Google, Authentik oder Okta.

### E neue Aabieter hinzuefüege

So füegsch e neue OIDC-Aabieter drzue:

1. **I d Istellige ga:** Gang uf **Settings**.
2. **OAuth-Bereich sueche:** Scroll bis zu **OAuth Authentication**.
3. **Aabieter hinzuefüege:** Klick uf **Add Provider**.

Du gsehsch de die Fäuder da:

* **Provider Type:** Isch `OpenID Connect (OIDC)`.
* **Issuer URL:** D Basis-URL vo dim OIDC-Aabieter. Über die erkennt DockFlare d Konfiguration automatisch.
* **Provider ID:** E churze, eindeutige Name wie `google` oder `authentik-corp`.
* **Display Name:** Dr Name, wo uf em Login-Button erscheint.
* **Client ID:** D öffentlechi Kennig vo dr DockFlare-App.
* **Client Secret:** S geheime Gägestück zur Client ID.
* **Enable Provider:** Aktiviert oder deaktiviert dr Aabieter.

Wänn aues stimmt, klicksch uf **Add Provider** zum speichere.

### D Callback-URL finde

Sobald dr Aabieter aagleit isch, wird d **Callback URL** under em Itrag aazeigt. Die heisst je nach Aabieter o **Authorized redirect URI**.

Du muesch die URL exakt so i dr Admin-Konsole vo dim Aabieter iiträge.

---

### Bispil: Google iirichte

So geit s mit Google:

1. **Google Cloud Console ufmache:** [APIs & Services > Credentials](https://console.cloud.google.com/apis/credentials)
2. **OAuth client ID erstelle**
3. **App-Typ uf `Web application` setze**
4. **Callback-URL iiträge**
5. **Client ID u Client Secret usekopiere**
6. **I DockFlare iiträge:**
   * **Issuer URL:** `https://accounts.google.com`
   * **Provider ID:** `google`
   * **Display Name:** `Google`
   * **Client ID:** `(Your Client ID from Google)`
   * **Client Secret:** `(Your Client Secret from Google)`

Speicher dä Aabieter. Nachhär chasch di mit dim Google-Konto aamälde.

---

### DockFlare mit OAuth u Access Policies kombiniere

Wänn du OAuth bruuchsch u glichzitig d Hauptoberflächi mit ere Access Policy schützt, muesch luege, dass d OAuth-Callbacks trotzdem no durechöme.

#### **Best Practice: Bypass für OAuth-Callbacks**

Bruuch indexierti Labels, zum für d Hauptoberflächi u d Callback-Pfäd getrennti Regle z ha:

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

#### **Warum das nötig isch**

- **D Hauptoberflächi blybt gschützt**
- **D OAuth-Callbacks funktioniere**
- **Nume d Callback-Pfäd wärde bypassed**
- **S funktioniert o mit IP- oder Login-basiertne Policies**

#### **Wichtigi Hinwys**

1. **Pfad muess exakt stimme**
2. **Für jede Aabieter e eigeti Callback-Regel**
3. **Kei Wildcards für Callback-Pfäd**
4. **Nachhär immer dr Login-Flow teste**
