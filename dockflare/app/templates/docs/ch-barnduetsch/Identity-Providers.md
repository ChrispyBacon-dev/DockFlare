# ID-Provider

> **📌 Wichtig:** Die Aaleitig erklärt, wie du **ID-Provider für Cloudflare Access Policies** iirichtisch, zum dini Dienscht u Aawändige z schütze. Wänn du OAuth/OIDC für d **Aamäldig a dr DockFlare Web UI** iirichte wotsch, lueg stattdesse i [OAuth-Provider iirichte](OAuth-Provider-Setup.md).

ID-Provider (IdPs) mache OAuth/OIDC-Authentifizierig für dini via Cloudflare Zero Trust gschützte Aawändige möglich. DockFlare vereinfacht d Verwaltig vo IdPs u ihri Iibindig i dini Access-Richtlinie.

## Überblick

Statt nume uf Mail-basierte Authentifizierig z setze, chasch gängigi OAuth-Provider wie Google, GitHub, Azure AD oder Okta bruuchen. Benutzer mälde sech mit ihrne bestehende Konten aa, was d Aamäldig bequemer u glychzitig sicher macht.

## Unterstützti Provider

DockFlare unterstützt aktuell:

* **Google** – privat Google-Konte
* **Google Workspace** – Google Workspace / G Suite mit optionale Domain-Iischränkig
* **Microsoft Azure AD** – Microsoft Entra ID (Azure Active Directory)
* **Okta** – Okta Identity Cloud
* **GitHub** – GitHub OAuth
* **Generischs OpenID Connect** – jede OIDC-kompatible Provider

## ID-Provider verwalte

### E ID-Provider derzue tue

1. Gang uf d Syte **Access Policies**.
2. Klick im Abschnitt **Identity Providers** uf **Add Provider**.
3. Füll d nötige Fälder uus:
   * **Friendly Name** – interne Name i DockFlare, zum Bispil `google-main` oder `github-dev`
   * **Display Name** – Name, wo im Cloudflare-Dashboard azeigt wird
   * **Provider Type** – dr Typ vom OAuth-Provider
   * **Configuration** – d provider-spezifische Zuegangsdaten gemäss dr Aaleitig wyter unde
4. Klick uf **Create Provider**.
5. Test dr Provider mit dr bereitgstellte Test-URL.

### Mit Cloudflare synchronisiere

Wänn du IdPs scho i Cloudflare Zero Trust iigrichtet hesch:

1. Klick im Abschnitt **Identity Providers** uf **Sync from Cloudflare**.
2. DockFlare importiert aui vorhandene IdPs u erstellt automatisch Friendly Names.
3. Nachhär chasch die Friendly Names umbenenne, damit si i Labels eifacher z bruuche sy.

### E ID-Provider teste

Nach em Erstelle vo mene IdP chasch ne grad teste:

1. Klick uf ds Menü **⋮** näb em Provider.
2. Wähl **Test IdP**.
3. Es geit es nöis Fänschter für d Authentifizierig uf.
4. Prüef, öb dr Aamäldig-Fluss korrekt funktioniert.

## Iirichtigs-Aaleitige pro Provider

### Google (privati Konte)

**Schritt 1: OAuth-Zuegangsdaten erstelle**

1. Mach d [Google Cloud Console](https://console.cloud.google.com/) uf.
2. Erstell es nöis Projekt oder wähl es bestehends us.
3. Gang zu **APIs & Services** → **Credentials**.
4. Klick uf **Create Credentials** → **OAuth client ID**.
5. Wähl **Web application**.
6. Füg die autorisierti Redirect-URI derzue:
   ```
   https://<your-team>.cloudflareaccess.com/cdn-cgi/access/callback
   ```
   <small>Dr Teamname isch i <a href="https://one.dash.cloudflare.com/{{ACCOUNT_ID}}/settings/custom_pages" target="_blank">Zero Trust</a> under Settings > Custom Pages z finde.</small>
7. Kopier **Client ID** u **Client Secret**.

**Schritt 2: I DockFlare iiträge**

* **Client ID**: dr Wert us dr Google Cloud Console
* **Client Secret**: dr Wert us dr Google Cloud Console

---

### Google Workspace

Gliich wie bi Google obe, aber mit eme zuesätzleche optionale Fäld:

* **Apps Domain**: optionali Iischränkig uf e bestimmti Domain, zum Bispil `example.com`

Wänn das Fäld gsetzt isch, chöi sech nume Benutzer mit `@example.com`-Adresse authentifiziere.

---

### Microsoft Azure AD

**Schritt 1: Aawändig i Azure registriere**

1. Mach ds [Azure Portal](https://portal.azure.com/) uf.
2. Gang zu **Azure Active Directory** → **App registrations**.
3. Klick uf **New registration**.
4. Gib dr Aawändig e Name, zum Bispil `DockFlare Access`.
5. Wähl under **Redirect URI** d Option **Web** u trag das ii:
   ```
   https://<your-team>.cloudflareaccess.com/cdn-cgi/access/callback
   ```
   <small>Dr Teamname isch i <a href="https://one.dash.cloudflare.com/{{ACCOUNT_ID}}/settings/custom_pages" target="_blank">Zero Trust</a> under Settings > Custom Pages z finde.</small>
6. Klick uf **Register**.
7. Kopier d **Application (client) ID**.
8. Kopier d **Directory (tenant) ID**.
9. Gang zu **Certificates & secrets** → **New client secret**.
10. Erstell es Secret u kopier dr **Value**.

**Schritt 2: I DockFlare iiträge**

* **Application (client) ID**: dr Wert us Azure
* **Directory (tenant) ID**: dr Wert us Azure
* **Client Secret**: dr Wert us Azure

---

### GitHub

**Schritt 1: OAuth-App erstelle**

1. Mach d [GitHub Developer Settings](https://github.com/settings/developers) uf.
2. Klick uf **New OAuth App**.
3. Füll d Fälder uus:
   * **Application name**: `DockFlare Access`
   * **Homepage URL**: `https://your-domain.com`
   * **Authorization callback URL**:
     ```
     https://<your-team>.cloudflareaccess.com/cdn-cgi/access/callback
     ```
     <small>Dr Teamname isch i <a href="https://one.dash.cloudflare.com/{{ACCOUNT_ID}}/settings/custom_pages" target="_blank">Zero Trust</a> under Settings > Custom Pages z finde.</small>
4. Klick uf **Register application**.
5. Kopier d **Client ID**.
6. Klick uf **Generate a new client secret** u kopier s Secret.

**Schritt 2: I DockFlare iiträge**

* **Client ID**: dr Wert us GitHub
* **Client Secret**: dr Wert us GitHub

---

### Okta

**Schritt 1: Aawändig i Okta erstelle**

1. Mäld di i dr [Okta Admin Console](https://admin.okta.com/) aa.
2. Gang zu **Applications** → **Create App Integration**.
3. Wähl **OIDC - OpenID Connect**.
4. Wähl **Web Application**.
5. Trag under **Sign-in redirect URIs** das ii:
   ```
   https://<your-team>.cloudflareaccess.com/cdn-cgi/access/callback
   ```
   <small>Dr Teamname isch i <a href="https://one.dash.cloudflare.com/{{ACCOUNT_ID}}/settings/custom_pages" target="_blank">Zero Trust</a> under Settings > Custom Pages z finde.</small>
6. Klick uf **Save**.
7. Kopier **Client ID** u **Client Secret**.
8. Notier dini **Okta-Domain**, zum Bispil `https://dev-12345.okta.com`.

**Schritt 2: I DockFlare iiträge**

* **Okta Account URL**: dini Okta-Domain, zum Bispil `https://dev-12345.okta.com`
* **Client ID**: dr Wert us Okta
* **Client Secret**: dr Wert us Okta

---

### Generischs OpenID Connect

Für jede OIDC-kompatible Provider:

**Schritt 1: Aabieter-Infos zämehole**

Hol us dr Doku vo dim IdP:

* Authorization URL
* Token URL
* JWKS URL (JSON Web Key Set)
* Client ID
* Client Secret

**Schritt 2: I DockFlare iiträge**

* **Authorization URL**: dr OAuth-Autorisierigsendpunkt vom Provider
* **Token URL**: dr Token-Endpunkt vom Provider
* **JWKS URL**: dr JWKS-Endpunkt für d Signaturprüefig
* **Client ID**: dr Provider-Wert
* **Client Secret**: dr Provider-Wert

---

## ID-Provider i Access Policies bruuche

### I Access Groups

1. Gang zu **Access Policies** → **Advanced Access Policies**.
2. Klick uf **Create New Group** oder bearbeit e bestehendi Gruppe.
3. Im Abschnitt **Policy Rules**:
   * **Identity Providers**: Wähl ei oder mehri IdPs uus
   * **Allowed Emails or Domains**: **Pflicht, wänn du IdPs bruuchsch**. Trag do die erlaubte Mailadresse ii.
4. Speicher d Gruppe.

### Authentifizierigs-Modi

Es git zwo üebligi Variante:

1. **Nume E-Mail**: Du tragisch Mailadresse ii u wählsch kei IdPs. D Benutzer authentifiziere sech de über e Einmal-PIN.
2. **IdP + E-Mail (Pflicht)**: Du wählsch ei oder mehri IdPs u definierisch glychzitig erlaubti Mailadresse. Benutzer müesse sech über dr gwählti IdP authentifiziere **u** i dr erlaubte Lischt sy.

**⚠️ Sicherhäitshinwys:** Wänn du ID-Provider bruuchsch, muesch immer erlaubti Mailadresse definiere. Sunst chönnt zum Bispil bi dr Uuswahl vo `Google` praktisch jede mit emene beliebige Google-Konto uf dyn Dienst zuegryfe.

### I Docker-Labels

Bruuch dr Friendly Name i de Labels vom Container:

```yaml
services:
  myapp:
    image: myapp:latest
    labels:
      dockflare.enable: "true"
      dockflare.hostname: "app.example.com"
      dockflare.access.group: "my-access-group"
```

D Zuegriffsgruppe `my-access-group` löst Friendly Names vo IdPs automatisch i Cloudflare-UUIDs uf.

---

## Best Practices

### Namenskonventione

Bruuch klari, verständlechi Name:

* ✅ `google-main`, `github-dev`, `azure-work`
* ❌ `idp1`, `test`, `new`

### Sicherhäit

* **Secrets regelmässig rotiere** – Client Secrets in sinnvolle Intervall erneuere
* **Umfang iischränke** – bi Google Workspace oder Azure AD dr Zuegriff wenn möglich uf bestimmti Domains begränze
* **Vor Produktion teste** – IdPs immer vor em produktive Iisatz prüefe
* **Nutzig überwache** – Cloudflare-Logs uf unautorisierte Zuegriffsversuech prüefe

### Mehri Umgebige

Erstell für jedi Umgebig eigeti IdPs:

* `google-dev` – Entwicklig
* `google-staging` – Staging
* `google-prod` – Produktion

### Mail-Anforderige bi IdPs

**WICHTIG:** IdP-Authentifizierig brucht us Sicherhäitsgründ immer Mail-Iischränkige.

**Bispiel für e Zuegriffsgruppe:**

* **Identity Providers**: `google-main`
* **Allowed Emails**: `admin@example.com, user@example.com, @contractor-domain.com`

Die Konfiguration erlaubt Zuegriff für Benutzer, wo:

* sech über dr IdP `google-main` (Google OAuth) authentifiziere **u**
* e Mailadresse hei, wo `admin@example.com`, `user@example.com` oder ere beliebige `@contractor-domain.com`-Adresse entspricht
