# Identitätsanbieter

> **📌 Wichtig:** Dieser Leitfaden beschreibt die Konfiguration von **Identitätsanbietern für Cloudflare Access Policies**, um Ihre Dienste und Anwendungen zu schützen. Wenn Sie OAuth/OIDC für die **Anmeldung an der DockFlare Web-UI** einrichten möchten, lesen Sie stattdessen [Einrichtung von OAuth-Anbietern](OAuth-Provider-Setup.md).

Identitätsanbieter (IdPs) ermöglichen OAuth/OIDC-Authentifizierung für Ihre durch Cloudflare Zero Trust geschützten Anwendungen. DockFlare erleichtert die Verwaltung von IdPs und deren Integration in Ihre Access-Richtlinien.

## Übersicht

Anstatt sich ausschließlich auf E-Mail-basierte Authentifizierung zu verlassen, können Sie gängige OAuth-Anbieter wie Google, GitHub, Azure AD und weitere verwenden. Benutzer melden sich mit ihren bestehenden Konten an, was ein nahtloses und sicheres Anmeldeerlebnis bietet.

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

1. Öffnen Sie die Seite **Access Policies**.
2. Klicken Sie im Abschnitt **Identity Providers** auf **Add Provider**.
3. Füllen Sie die erforderlichen Felder aus:
   - **Friendly Name**: interner Name in DockFlare, zum Beispiel `google-main` oder `github-dev`
   - **Display Name**: Name, der im Cloudflare-Dashboard angezeigt wird
   - **Provider Type**: Wählen Sie Ihren OAuth-Anbieter aus
   - **Configuration**: Anbieter-spezifische Zugangsdaten gemäß den untenstehenden Anleitungen
4. Klicken Sie auf **Create Provider**.
5. Testen Sie den Anbieter mit der bereitgestellten Test-URL.

### Mit Cloudflare synchronisieren

Wenn Sie IdPs bereits in Cloudflare Zero Trust eingerichtet haben:

1. Klicken Sie im Abschnitt Identity Providers auf **Sync from Cloudflare**.
2. DockFlare importiert alle vorhandenen IdPs und erzeugt automatisch Friendly Names.
3. Anschließend können Sie diese Friendly Names umbenennen, damit sie in Labels leichter zu verwenden sind.

### Einen Identitätsanbieter testen

Nach dem Erstellen eines IdP können Sie ihn direkt testen:

1. Klicken Sie auf das Menü **⋮** neben dem Anbieter.
2. Wählen Sie **Test IdP**.
3. Es öffnet sich ein neues Fenster zur Authentifizierung.
4. Prüfen Sie, ob der Anmeldefluss korrekt funktioniert.

## Einrichtungsanleitungen für Anbieter

### Google (private Konten)

**Schritt 1: OAuth-Anmeldedaten erstellen**

1. Öffnen Sie die [Google Cloud Console](https://console.cloud.google.com/).
2. Erstellen Sie ein neues Projekt oder wählen Sie ein bestehendes aus.
3. Gehen Sie zu **APIs & Services** → **Credentials**.
4. Klicken Sie auf **Create Credentials** → **OAuth client ID**.
5. Wählen Sie **Web application**.
6. Fügen Sie die autorisierte Redirect-URI hinzu:
   ```
   https://<your-team>.cloudflareaccess.com/cdn-cgi/access/callback
   ```
   <small>Den Teamnamen finden Sie in <a href="https://one.dash.cloudflare.com/{{ACCOUNT_ID}}/settings/custom_pages" target="_blank">Zero Trust</a> unter Settings > Custom Pages.</small>
7. Kopieren Sie **Client ID** und **Client Secret**.

**Schritt 2: In DockFlare konfigurieren**

- **Client ID**: Wert aus der Google Cloud Console einfügen
- **Client Secret**: Wert aus der Google Cloud Console einfügen

---

### Google Workspace

Wie bei Google oben, aber mit einem zusätzlichen optionalen Feld:

- **Apps Domain**: (Optional) Beschränkung auf eine bestimmte Domain, zum Beispiel `example.com`

Wenn dieses Feld gesetzt ist, können sich nur Benutzer mit `@example.com`-Adressen authentifizieren.

---

### Microsoft Azure AD

**Schritt 1: Anwendung in Azure registrieren**

1. Öffnen Sie das [Azure Portal](https://portal.azure.com/).
2. Gehen Sie zu **Azure Active Directory** → **App registrations**.
3. Klicken Sie auf **New registration**.
4. Geben Sie Ihrer Anwendung einen Namen, zum Beispiel `DockFlare Access`.
5. Wählen Sie unter **Redirect URI** die Option **Web** und tragen Sie ein:
   ```
   https://<your-team>.cloudflareaccess.com/cdn-cgi/access/callback
   ```
   <small>Den Teamnamen finden Sie in <a href="https://one.dash.cloudflare.com/{{ACCOUNT_ID}}/settings/custom_pages" target="_blank">Zero Trust</a> unter Settings > Custom Pages.</small>
6. Klicken Sie auf **Register**.
7. Kopieren Sie die **Application (client) ID**.
8. Kopieren Sie die **Directory (tenant) ID**.
9. Gehen Sie zu **Certificates & secrets** → **New client secret**.
10. Erstellen Sie ein Secret und kopieren Sie den **Value**.

**Schritt 2: In DockFlare konfigurieren**

- **Application (client) ID**: Wert aus Azure einfügen
- **Directory (tenant) ID**: Wert aus Azure einfügen
- **Client Secret**: Wert aus Azure einfügen

---

### GitHub

**Schritt 1: OAuth-App erstellen**

1. Öffnen Sie die [GitHub Developer Settings](https://github.com/settings/developers).
2. Klicken Sie auf **New OAuth App**.
3. Füllen Sie die Felder aus:
   - **Application name**: DockFlare Access
   - **Homepage URL**: `https://your-domain.com`
   - **Authorization callback URL**:
     ```
     https://<your-team>.cloudflareaccess.com/cdn-cgi/access/callback
     ```
     <small>Den Teamnamen finden Sie in <a href="https://one.dash.cloudflare.com/{{ACCOUNT_ID}}/settings/custom_pages" target="_blank">Zero Trust</a> unter Settings > Custom Pages.</small>
4. Klicken Sie auf **Register application**.
5. Kopieren Sie die **Client ID**.
6. Klicken Sie auf **Generate a new client secret** und kopieren Sie das Secret.

**Schritt 2: In DockFlare konfigurieren**

- **Client ID**: Wert aus GitHub einfügen
- **Client Secret**: Wert aus GitHub einfügen

---

### Okta

**Schritt 1: Anwendung in Okta erstellen**

1. Melden Sie sich in Ihrer [Okta Admin Console](https://admin.okta.com/) an.
2. Gehen Sie zu **Applications** → **Create App Integration**.
3. Wählen Sie **OIDC - OpenID Connect**.
4. Wählen Sie **Web Application**.
5. Konfigurieren Sie:
   - **Sign-in redirect URIs**:
     ```
     https://<your-team>.cloudflareaccess.com/cdn-cgi/access/callback
     ```
     <small>Den Teamnamen finden Sie in <a href="https://one.dash.cloudflare.com/{{ACCOUNT_ID}}/settings/custom_pages" target="_blank">Zero Trust</a> unter Settings > Custom Pages.</small>
6. Klicken Sie auf **Save**.
7. Kopieren Sie **Client ID** und **Client Secret**.
8. Notieren Sie sich Ihre **Okta-Domain**, zum Beispiel `https://dev-12345.okta.com`.

**Schritt 2: In DockFlare konfigurieren**

- **Okta Account URL**: Ihre Okta-Domain, zum Beispiel `https://dev-12345.okta.com`
- **Client ID**: Wert aus Okta einfügen
- **Client Secret**: Wert aus Okta einfügen

---

### Generisches OpenID Connect

Für jeden OIDC-kompatiblen Anbieter:

**Schritt 1: Anbieter-Konfiguration abrufen**

Beschaffen Sie sich aus der Dokumentation Ihres IdP:
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

1. Gehen Sie zu **Access Policies** → **Advanced Access Policies**.
2. Klicken Sie auf **Create New Group** oder bearbeiten Sie eine bestehende Gruppe.
3. Im Abschnitt **Policy Rules**:
   - **Identity Providers**: Wählen Sie einen oder mehrere IdPs aus
   - **Allowed Emails or Domains**: **Erforderlich bei Verwendung von IdPs**. Geben Sie die erlaubten E-Mail-Adressen an.
4. Speichern Sie die Gruppe.

### Authentifizierungsmodi

Es gibt zwei Möglichkeiten:

1. **Nur E-Mail**: Geben Sie E-Mail-Adressen ein und wählen Sie keine IdPs aus. Benutzer authentifizieren sich dann per Einmal-PIN.
2. **IdP + E-Mail (erforderlich)**: Wählen Sie einen oder mehrere IdPs aus und geben Sie erlaubte E-Mail-Adressen an. Benutzer müssen sich über den ausgewählten IdP authentifizieren und in der Liste der erlaubten Adressen enthalten sein.

**⚠️ Sicherheitshinweis:** Wenn Sie Identitätsanbieter verwenden, **müssen** Sie erlaubte E-Mail-Adressen festlegen. Andernfalls könnte zum Beispiel bei Auswahl von `Google` jeder Benutzer mit einem beliebigen Google-Konto auf Ihren Dienst zugreifen.

### In Docker-Labels

Verwenden Sie den Friendly Name in den Labels Ihrer Container:

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

Verwenden Sie klare und aussagekräftige Namen:
- ✅ `google-main`, `github-dev`, `azure-work`
- ❌ `idp1`, `test`, `new`

### Sicherheit

- **Secrets regelmäßig rotieren**: Aktualisieren Sie Client Secrets in festen Abständen
- **Umfang einschränken**: Begrenzen Sie bei Google Workspace und Azure AD den Zugriff nach Möglichkeit auf bestimmte Domains
- **Vor Produktion testen**: Testen Sie IdPs immer, bevor Sie sie für produktive Dienste einsetzen
- **Nutzung überwachen**: Prüfen Sie Cloudflare-Logs auf unautorisierte Zugriffsversuche

### Mehrere Umgebungen

Erstellen Sie getrennte IdPs für verschiedene Umgebungen:
- `google-dev` - Entwicklungsumgebung
- `google-staging` - Staging-Umgebung
- `google-prod` - Produktionsumgebung

### E-Mail-Anforderungen bei IdPs

**WICHTIG:** Die IdP-Authentifizierung erfordert aus Sicherheitsgründen immer E-Mail-Beschränkungen.

**Beispiel für eine Zugriffsgruppe:**
- **Identity Providers**: `google-main`
- **Allowed Emails**: `admin@example.com, user@example.com, @contractor-domain.com`

Diese Konfiguration erlaubt Zugriff für Benutzer, die:
- sich über den IdP `google-main` (Google OAuth) authentifizieren **und**
- eine E-Mail-Adresse besitzen, die `admin@example.com`, `user@example.com` oder einer beliebigen `@contractor-domain.com`-Adresse entspricht

**So funktioniert es:**
1. Der Benutzer klickt in Ihrer geschützten Anwendung auf „Anmelden“.
2. Er wird zum Google-OAuth-Login weitergeleitet.
3. Nach der Google-Authentifizierung prüft Cloudflare, ob die E-Mail-Adresse in der Liste der erlaubten Adressen enthalten ist.
4. Zugriff wird nur gewährt, wenn die E-Mail-Adresse zur erlaubten Liste passt.

---

## Fehlerbehebung

### Fehler „Invalid Redirect URI“

**Ursache:** Die beim OAuth-Anbieter eingetragene Redirect-URI stimmt nicht mit der von Cloudflare erwarteten URI überein.

**Lösung:** Stellen Sie sicher, dass exakt diese Redirect-URI hinterlegt ist:
```
https://<your-team>.cloudflareaccess.com/cdn-cgi/access/callback
```
<small>Den Teamnamen finden Sie in <a href="https://one.dash.cloudflare.com/{{ACCOUNT_ID}}/settings/custom_pages" target="_blank">Zero Trust</a> unter Settings > Custom Pages.</small>

Ersetzen Sie `<your-team>` durch den Namen Ihres Cloudflare Zero Trust Teams.

---

### „IdP Test Failed“

**Ursache:** Falsche Zugangsdaten oder fehlerhafte Konfiguration.

**Lösung:**
1. Prüfen Sie, ob Client ID und Client Secret korrekt sind.
2. Stellen Sie sicher, dass die OAuth-Anwendung beim Anbieter aktiviert ist.
3. Prüfen Sie bei Azure AD sowohl Client ID als auch Tenant ID.
4. Testen Sie den Anbieter mit der Cloudflare-Test-URL.

---

### „Cannot Delete System-Managed IdP“

**Ursache:** Es wird versucht, den integrierten One-Time-PIN-Anbieter zu löschen.

**Lösung:** Der Anbieter `onetimepin` ist systemverwaltet und kann nicht gelöscht werden. Er wird für OTP-Authentifizierung per E-Mail benötigt.

---

### „IdP Not Found in Docker Label“

**Ursache:** Im Label wird eine Cloudflare-UUID statt des Friendly Name verwendet.

**Lösung:** Verwenden Sie in der Konfiguration der Zugriffsgruppe den Friendly Name, zum Beispiel `google-main`, anstelle der UUID.

---

## Verwandte Dokumentation

- [Best Practices für Access Policies](Access-Policy-Best-Practices.md)
- [Zonen-Standardrichtlinien](Zone-Default-Policies.md)
- [Container-Labels](Container-Labels.md)
- [Sicherheitsarchitektur & Härtung](Security-Architecture.md)

---
