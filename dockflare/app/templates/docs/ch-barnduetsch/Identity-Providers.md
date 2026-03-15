# Identitätsanbieter

> **📌 Wichtig:** Dieser Leitfaden beschreibt die Konfiguration von **Identitätsanbietern für Cloudflare Access Policies**, um dini Dienste u Anwendungen zu schützen. Wänn du OAuth/OIDC für die **Anmeldung an der DockFlare Web UI** einrichten wotsch, läs stattdessen [Einrichtung von OAuth-Anbietern](OAuth-Provider-Setup.md).

Identitätsanbieter (IdPs) ermöglichen OAuth/OIDC-Authentifizierung für dini durch Cloudflare Zero Trust geschützten Anwendungen. DockFlare erleichtert die Verwaltung von IdPs u deren Integration in dini Access-Richtlinien.

## Überblick

Anstatt sich ausschliesslich auf E-Mail-basierte Authentifizierung zu verlassen, chasch gängige OAuth-Anbieter wie Google, GitHub, Azure AD u weitere bruuche. Benutzer melden sich mit ihren bestehenden Konten an, was ein nahtloses u sicheres Anmeldeerlebnis bietet.

## Unterstützte Anbieter

DockFlare unterstützt die folgenden Identitätsanbieter:

- **Google** - Private Google-Konten
- **Google Workspace** - Google Workspace (G Suite)-Konten mit optionaler Domain-Beschränkung
- **Microsoft Azure AD** - Microsoft Entra ID (Azure Active Directory)
- **Okta** - Okta Identity Cloud
- **GitHub** - GitHub OAuth
- **Generisches OpenID Connect** - Jeder OIDC-kompatible Anbieter

## Verwaltung von Identitätsanbietern

### Einen Identitätsanbieter hinzufügen

1. Mach uf die Seite **Access Policies**.
2. Klick im Abschnitt **Identity Providers** auf **Add Provider**.
3. Füll die erforderlichen Felder aus:
   - **Friendly Name**: interner Name in DockFlare, zum Biispil `google-main` oder `github-dev`
   - **Display Name**: Name, der im Cloudflare-Dashboard angezeigt wird
   - **Provider Type**: Wähl dini OAuth-Anbieter aus
   - **Configuration**: Anbieter-spezifische Zugangsdaten gemäss den untenstehenden Anleitungen
4. Klick auf **Create Provider**.
5. Test den Anbieter mit der bereitgestellten Test-URL.

### Mit Cloudflare synchronisieren

Wänn du IdPs bereits i Cloudflare Zero Trust iigrichtet hesch:

1. Klick im Abschnitt Identity Providers auf **Sync from Cloudflare**.
2. DockFlare importiert alle vorhandenen IdPs u erzeugt automatisch Friendly Names.
3. Nachhär chasch diese Friendly Names umbenennen, damit sie in Labels leichter zu bruuche si.

### Einen Identitätsanbieter testen

Nach dem Erstellen eines IdP chasch ihn direkt testen:

1. Klick auf das Menü **⋮** neben dem Anbieter.
2. Wähl **Test IdP**.
3. Es öffnet sich ein neues Fenster zur Authentifizierung.
4. Prüef, öb der Anmeldefluss korrekt funktioniert.

## Einrichtungsanleitungen für Anbieter

### Google (private Konten)

**Schritt 1: OAuth-Anmeldedaten erstellen**

1. Mach uf die [Google Cloud Console](https://console.cloud.google.com/).
2. Erstell ein neues Projekt oder wähl ein bestehendes aus.
3. Gang zu **APIs & Services** → **Credentials**.
4. Klick auf **Create Credentials** → **OAuth client ID**.
5. Wähl **Web application**.
6. Füg die autorisierte Redirect-URI hinzu:
   ```
   https://<your-team>.cloudflareaccess.com/cdn-cgi/access/callback
   ```
   <small>Den Teamnamen findsch in <a href="https://one.dash.cloudflare.com/{{ACCOUNT_ID}}/settings/custom_pages" target="_blank">Zero Trust</a> unter Settings > Custom Pages.</small>
7. Kopier **Client ID** u **Client Secret**.

**Schritt 2: In DockFlare konfigurieren**

- **Client ID**: Wert aus der Google Cloud Console einfügen
- **Client Secret**: Wert aus der Google Cloud Console einfügen

---

### Google Workspace

Wie bei Google oben, aber mit einem zusätzlichen optionalen Feld:

- **Apps Domain**: (Optional) Beschränkung auf eine bestimmte Domain, zum Biispil `example.com`

Wenn dieses Feld gesetzt isch, chöi sich nur Benutzer mit `@example.com`-Adressen authentifizieren.

---

### Microsoft Azure AD

**Schritt 1: Anwendung in Azure registrieren**

1. Mach uf das [Azure Portal](https://portal.azure.com/).
2. Gang zu **Azure Active Directory** → **App registrations**.
3. Klick auf **New registration**.
4. Gib dinere Anwendung einen Namen, zum Biispil `DockFlare Access`.
5. Wähl unter **Redirect URI** die Option **Web** u trag ein:
   ```
   https://<your-team>.cloudflareaccess.com/cdn-cgi/access/callback
   ```
   <small>Den Teamnamen findsch in <a href="https://one.dash.cloudflare.com/{{ACCOUNT_ID}}/settings/custom_pages" target="_blank">Zero Trust</a> unter Settings > Custom Pages.</small>
6. Klick auf **Register**.
7. Kopier die **Application (client) ID**.
8. Kopier die **Directory (tenant) ID**.
9. Gang zu **Certificates & secrets** → **New client secret**.
10. Erstell es Secret u kopier dr den **Value**.

**Schritt 2: In DockFlare konfigurieren**

- **Application (client) ID**: Wert aus Azure einfügen
- **Directory (tenant) ID**: Wert aus Azure einfügen
- **Client Secret**: Wert aus Azure einfügen

---

### GitHub

**Schritt 1: OAuth-App erstellen**

1. Mach uf die [GitHub Developer Settings](https://github.com/settings/developers).
2. Klick auf **New OAuth App**.
3. Füll die Felder aus:
   - **Application name**: DockFlare Access
   - **Homepage URL**: `https://your-domain.com`
   - **Authorization callback URL**:
     ```
     https://<your-team>.cloudflareaccess.com/cdn-cgi/access/callback
     ```
     <small>Den Teamnamen findsch in <a href="https://one.dash.cloudflare.com/{{ACCOUNT_ID}}/settings/custom_pages" target="_blank">Zero Trust</a> unter Settings > Custom Pages.</small>
4. Klick auf **Register application**.
5. Kopier die **Client ID**.
6. Klick uf **Generate a new client secret** u kopier s'Secret.

**Schritt 2: In DockFlare konfigurieren**

- **Client ID**: Wert aus GitHub einfügen
- **Client Secret**: Wert aus GitHub einfügen

---

### Okta

**Schritt 1: Anwendung in Okta erstellen**

1. Mäld di aa in dinere [Okta Admin Console](https://admin.okta.com/) an.
2. Gang zu **Applications** → **Create App Integration**.
3. Wähl **OIDC - OpenID Connect**.
4. Wähl **Web Application**.
5. Konfigurier:
   - **Sign-in redirect URIs**:
     ```
     https://<your-team>.cloudflareaccess.com/cdn-cgi/access/callback
     ```
     <small>Den Teamnamen findsch in <a href="https://one.dash.cloudflare.com/{{ACCOUNT_ID}}/settings/custom_pages" target="_blank">Zero Trust</a> unter Settings > Custom Pages.</small>
6. Klick auf **Save**.
7. Kopier **Client ID** u **Client Secret**.
8. Notier dr dini **Okta-Domain**, zum Biispil `https://dev-12345.okta.com`.

**Schritt 2: In DockFlare konfigurieren**

- **Okta Account URL**: dini Okta-Domain, zum Biispil `https://dev-12345.okta.com`
- **Client ID**: Wert aus Okta einfügen
- **Client Secret**: Wert aus Okta einfügen

---

### Generisches OpenID Connect

Für jeden OIDC-kompatiblen Anbieter:

**Schritt 1: Anbieter-Konfiguration abrufen**

Hol dr us dr Doku vo dim IdP:
- Authorization URL
- Token URL
- JWKS URL (JSON Web Key Set)
- Client ID
- Client Secret

**Schritt 2: In DockFlare konfigurieren**

- **Authorization URL**: OAuth-Autorisierungsendpunkt des Anbieters
- **Token URL**: Token-Endpunkt des Anbieters
- **JWKS URL**: JWKS-Endpunkt des Anbieters zur Signaturprüfung
- **Client ID**: Wert des Anbieters
- **Client Secret**: Wert des Anbieters

---

## Verwendung von Identitätsanbietern in Access Policies

### In Access Groups

1. Gang zu **Access Policies** → **Advanced Access Policies**.
2. Klick uf **Create New Group** oder bearbeit e bestehendi Gruppe.
3. Im Abschnitt **Policy Rules**:
   - **Identity Providers**: Wähl einen oder mehrere IdPs aus
   - **Allowed Emails or Domains**: **Nötig bei Verwendung von IdPs**. Gib die erlaubten E-Mail-Adressen an.
4. Speicher die Gruppe.

### Authentifizierungsmodi

Es gibt zwei Möglichkeiten:

1. **Nur E-Mail**: Gib E-Mail-Adressen ein u wähl kener IdPs aus. Benutzer authentifizieren sich dann per Einmal-PIN.
2. **IdP + E-Mail (nötig)**: Wähl einen oder mehrere IdPs us u gib erlaubt E-Mail-Adrässä aa. Benutzer müesse sich über dä gwählti IdP authentifiziere u i dr Liste vo de erlaubte Adrässä sii.

**⚠️ Sicherheitshinweis:** Wänn du Identitätsanbieter bruuche, **müesse** du erlaubte E-Mail-Adressen festlegen. Andernfalls könnte zum Biispil bei Auswahl von `Google` jeder Benutzer mit einem beliebigen Google-Konto auf dini Dienst zugreifen.

### In Docker-Labels

Bruuch den Friendly Name in den Labels dinere Container:

```yaml
services:
  myapp:
    image: myapp:latest
    labels:
      dockflare.enable: "true"
      dockflare.hostname: "app.example.com"
      dockflare.access.group: "my-access-group"
```

Die Zugriffsgruppe `my-access-group` löst Friendly Names von IdPs automatisch in Cloudflare-UUIDs auf.

---

## Best Practices

### Namenskonventionen

Bruuch klare u aussagekräftige Namen:
- ✅ `google-main`, `github-dev`, `azure-work`
- ❌ `idp1`, `test`, `new`

### Sicherheit

- **Secrets regelmässig rotieren**: Aktualisier Client Secrets in festen Abständen
- **Umfang iischränke**: Begrenz bi Google Workspace u Azure AD dr Zuegriff wenn möglich uf bestimmti Domains
- **Vor Produktion testen**: Test IdPs immer, bevor du sie für produktive Dienste einsetzen
- **Nutzung überwachen**: Prüef Cloudflare-Logs auf unautorisierte Zugriffsversuche

### Mehrere Umgebungen

Erstell getrennte IdPs für verschiedene Umgebungen:
- `google-dev` - Entwicklungsumgebung
- `google-staging` - Staging-Umgebung
- `google-prod` - Produktionsumgebung

### E-Mail-Anforderungen bei IdPs

**WICHTIG:** Die IdP-Authentifizierung erfordert aus Sicherheitsgründen immer E-Mail-Beschränkungen.

**Beispiel für eine Zugriffsgruppe:**
- **Identity Providers**: `google-main`
- **Allowed Emails**: `admin@example.com, user@example.com, @contractor-domain.com`

Diese Konfiguration erlaubt Zugriff für Benutzer, die:
- sich über den IdP `google-main` (Google OAuth) authentifizieren **u**
- eine E-Mail-Adresse besitzen, die `admin@example.com`, `user@example.com` oder einer beliebigen `@contractor-domain.com`-Adresse entspricht

**So funktioniert es:**
1. Der Benutzer klickt in dinere geschützten Anwendung auf „Anmelden“.
2. Er wird zum Google-OAuth-Login weitergeleitet.
3. Nach der Google-Authentifizierung prüft Cloudflare, öb die E-Mail-Adresse in der Liste der erlaubten Adressen enthalten isch.
4. Zugriff wird nur gewährt, wenn die E-Mail-Adresse zur erlaubten Liste passt.

---

## Problem löse

### Fehler „Invalid Redirect URI“

**Ursache:** Die beim OAuth-Anbieter eingetragene Redirect-URI stimmt nid mit der von Cloudflare erwarteten URI überein.

**Lösung:** lueg dass exakt diese Redirect-URI hinterlegt isch:
```
https://<your-team>.cloudflareaccess.com/cdn-cgi/access/callback
```
<small>Den Teamnamen findsch in <a href="https://one.dash.cloudflare.com/{{ACCOUNT_ID}}/settings/custom_pages" target="_blank">Zero Trust</a> unter Settings > Custom Pages.</small>

Ersetz `<your-team>` durch den Namen din Cloudflare Zero Trust Teams.

---

### „IdP Test Failed“

**Ursache:** Falsche Zugangsdaten oder fehlerhafte Konfiguration.

**Lösung:**
1. Prüef, öb Client ID u Client Secret korrekt si.
2. lueg dass die OAuth-Anwendung beim Anbieter aktiviert isch.
3. Prüef bei Azure AD sowohl Client ID als auch Tenant ID.
4. Test den Anbieter mit der Cloudflare-Test-URL.

---

### „Cannot Delete System-Managed IdP“

**Ursache:** Es wird versucht, den integrierten One-Time-PIN-Anbieter zu löschen.

**Lösung:** Der Anbieter `onetimepin` isch systemverwaltet u cha nid gelöscht wärde. Er wird für OTP-Authentifizierung per E-Mail benötigt.

---

### „IdP Not Found in Docker Label“

**Ursache:** Im Label wird eine Cloudflare-UUID statt des Friendly Name verwendet.

**Lösung:** Bruuch in der Konfiguration der Zugriffsgruppe den Friendly Name, zum Biispil `google-main`, anstelle der UUID.

---

## Verwandte Doku

- [Best Practices für Access Policies](Access-Policy-Best-Practices.md)
- [Zonen-Standardrichtlinien](Zone-Default-Policies.md)
- [Container-Labels](Container-Labels.md)
- [Sicherheitsarchitektur & Härtung](Security-Architecture.md)

---
