# Poskytovatelia identity

> **📌 Dôležité:** Táto príručka je o konfigurácii **poskytovateľov identity pre Cloudflare Access politiky** na ochranu tvojich služieb/aplikácií. Ak chceš nastaviť OAuth/OIDC pre **prihlásenie do webového rozhrania DockFlare**, pozri radšej [Nastavenie poskytovateľa OAuth](help/OAuth-Provider-Setup.md).

Poskytovatelia identity (IdP) umožňujú OAuth/OIDC overovanie pre tvoje aplikácie chránené cez Cloudflare Zero Trust. DockFlare uľahčuje správu IdP a ich integráciu do tvojich prístupových politík.

## Prehľad

Namiesto spoliehania sa výhradne na overovanie e-mailom môžeš použiť populárnych OAuth providerov ako Google, GitHub, Azure AD a ďalších. Používatelia sa overia cez svoje existujúce účty, čo poskytuje plynulý a bezpečný zážitok z prihlásenia.

## Podporovaní provideri

DockFlare podporuje týchto poskytovateľov identity:

- **Google** – bežné Google účty
- **Google Workspace** – účty Google Workspace (G Suite) s voliteľným obmedzením domény
- **Microsoft Azure AD** – Microsoft Entra ID (Azure Active Directory)
- **Okta** – Okta Identity Cloud
- **GitHub** – GitHub OAuth
- **Generický OpenID Connect** – ktorýkoľvek provider kompatibilný s OIDC

## Správa poskytovateľov identity

### Pridanie poskytovateľa identity

1. Prejdi na stránku **Prístupové politiky**
2. V sekcii **Poskytovatelia identity** klikni na **Pridať providera**
3. Vyplň povinné polia:
   - **Priateľský názov**: Interný názov pre DockFlare (napr. `google-main`, `github-dev`)
   - **Zobrazovaný názov**: Názov zobrazený v Cloudflare dashboarde
   - **Typ providera**: Vyber svojho poskytovateľa OAuth
   - **Konfigurácia**: Prihlasovacie údaje špecifické pre providera (pozri príručky nastavenia nižšie)
4. Klikni na **Vytvoriť providera**
5. Otestuj providera pomocou poskytnutej testovacej URL

### Synchronizácia z Cloudflare

Ak už máš IdP nakonfigurovaných v Cloudflare Zero Trust:

1. Klikni na **Synchronizovať z Cloudflare** v sekcii Poskytovatelia identity
2. DockFlare naimportuje všetkých existujúcich IdP a automaticky vygeneruje priateľské názvy
3. Priateľské názvy môžeš premenovať pre ľahšie odkazovanie v labeloch

### Testovanie poskytovateľa identity

Po vytvorení IdP ho môžeš otestovať:

1. Klikni na menu **⋮** vedľa providera
2. Vyber **Testovať IdP**
3. Otvorí sa nové okno, kde sa môžeš overiť
4. Over, že prihlasovací tok funguje správne

## Príručky nastavenia providerov

### Google (bežné účty)

**Krok 1: Vytvor OAuth prihlasovacie údaje**

1. Prejdi do [Google Cloud Console](https://console.cloud.google.com/)
2. Vytvor nový projekt alebo vyber existujúci
3. Prejdi na **APIs & Services** → **Credentials**
4. Klikni na **Create Credentials** → **OAuth client ID**
5. Vyber **Web application**
6. Pridaj autorizovanú redirect URI:
   ```
   https://<your-team>.cloudflareaccess.com/cdn-cgi/access/callback
   ```
   <small>Názov svojho tímu nájdeš v <a href="https://dash.cloudflare.com/{{ACCOUNT_ID}}/one/settings/custom_pages" target="_blank">Zero Trust</a> pod Settings > Custom Pages.</small>
7. Skopíruj **Client ID** a **Client Secret**

**Krok 2: Nastav v DockFlare**

- **Client ID**: Vlož z Google Cloud Console
- **Client Secret**: Vlož z Google Cloud Console

---

### Google Workspace

Rovnako ako nastavenie Google vyššie, s jedným ďalším voliteľným poľom:

- **Apps Domain**: (Voliteľné) Obmedz na konkrétnu doménu (napr. `example.com`)

Ak je zadané, overiť sa môžu len používatelia s e-mailovými adresami `@example.com`.

---

### Microsoft Azure AD

**Krok 1: Zaregistruj aplikáciu v Azure**

1. Prejdi do [Azure Portal](https://portal.azure.com/)
2. Prejdi na **Azure Active Directory** → **App registrations**
3. Klikni na **New registration**
4. Pomenuj svoju aplikáciu (napr. „DockFlare Access“)
5. Pod **Redirect URI** vyber **Web** a zadaj:
   ```
   https://<your-team>.cloudflareaccess.com/cdn-cgi/access/callback
   ```
   <small>Názov svojho tímu nájdeš v <a href="https://dash.cloudflare.com/{{ACCOUNT_ID}}/one/settings/custom_pages" target="_blank">Zero Trust</a> pod Settings > Custom Pages.</small>
6. Klikni na **Register**
7. Skopíruj **Application (client) ID**
8. Skopíruj **Directory (tenant) ID**
9. Prejdi na **Certificates & secrets** → **New client secret**
10. Vytvor secret a skopíruj **Value**

**Krok 2: Nastav v DockFlare**

- **Application (client) ID**: Vlož z Azure
- **Directory (tenant) ID**: Vlož z Azure
- **Client Secret**: Vlož z Azure

---

### GitHub

**Krok 1: Vytvor OAuth aplikáciu**

1. Prejdi do [GitHub Developer Settings](https://github.com/settings/developers)
2. Klikni na **New OAuth App**
3. Vyplň údaje:
   - **Application name**: DockFlare Access
   - **Homepage URL**: `https://tvoja-domena.com`
   - **Authorization callback URL**:
     ```
     https://<your-team>.cloudflareaccess.com/cdn-cgi/access/callback
     ```
     <small>Názov svojho tímu nájdeš v <a href="https://dash.cloudflare.com/{{ACCOUNT_ID}}/one/settings/custom_pages" target="_blank">Zero Trust</a> pod Settings > Custom Pages.</small>
4. Klikni na **Register application**
5. Skopíruj **Client ID**
6. Klikni na **Generate a new client secret** a skopíruj ho

**Krok 2: Nastav v DockFlare**

- **Client ID**: Vlož z GitHubu
- **Client Secret**: Vlož z GitHubu

---

### Okta

**Krok 1: Vytvor aplikáciu v Okta**

1. Prihlás sa do svojej [Okta Admin Console](https://admin.okta.com/)
2. Prejdi na **Applications** → **Create App Integration**
3. Vyber **OIDC - OpenID Connect**
4. Zvoľ **Web Application**
5. Nakonfiguruj:
   - **Sign-in redirect URIs**:
     ```
     https://<your-team>.cloudflareaccess.com/cdn-cgi/access/callback
     ```
     <small>Názov svojho tímu nájdeš v <a href="https://dash.cloudflare.com/{{ACCOUNT_ID}}/one/settings/custom_pages" target="_blank">Zero Trust</a> pod Settings > Custom Pages.</small>
6. Klikni na **Save**
7. Skopíruj **Client ID** a **Client Secret**
8. Poznač si svoju **Okta doménu** (napr. `https://dev-12345.okta.com`)

**Krok 2: Nastav v DockFlare**

- **Okta Account URL**: Tvoja Okta doména (napr. `https://dev-12345.okta.com`)
- **Client ID**: Vlož z Okta
- **Client Secret**: Vlož z Okta

---

### Generický OpenID Connect

Pre ktoréhokoľvek providera kompatibilného s OIDC:

**Krok 1: Získaj konfiguráciu providera**

Z dokumentácie svojho IdP získaj:
- Authorization URL
- Token URL
- JWKS URL (JSON Web Key Set)
- Client ID
- Client Secret

**Krok 2: Nastav v DockFlare**

- **Authorization URL**: OAuth autorizačný endpoint providera
- **Token URL**: Token endpoint providera
- **JWKS URL**: JWKS endpoint providera (na overenie podpisu)
- **Client ID**: Od tvojho providera
- **Client Secret**: Od tvojho providera

---

## Používanie poskytovateľov identity v prístupových politikách

### V prístupových skupinách

1. Prejdi na **Prístupové politiky** → **Pokročilé prístupové politiky**
2. Klikni na **Vytvoriť novú skupinu** alebo uprav existujúcu skupinu
3. V sekcii **Pravidlá politiky**:
   - **Poskytovatelia identity**: Vyber jedného alebo viacerých IdP
   - **Povolené e-maily alebo domény**: **Povinné pri použití IdP** – zadaj povolené e-mailové adresy
4. Ulož skupinu

### Režimy overovania

Máš dve možnosti:

1. **Len e-mail**: Zadaj e-maily, nevyber žiadneho IdP – používatelia sa overia jednorazovým PIN
2. **IdP + e-mail (povinné)**: Vyber IdP A zadaj povolené e-maily – používatelia sa musia overiť cez zvoleného IdP A byť v zozname povolených e-mailov

**⚠️ Bezpečnostné upozornenie**: Pri použití poskytovateľov identity **musíš** zadať povolené e-mailové adresy. Zabraňuje to neoprávnenému prístupu – napríklad bez obmedzenia e-mailom by výber „Google“ ako IdP umožnil prístup k tvojej službe komukoľvek s akýmkoľvek Google účtom.

### V Docker labeloch

Použi priateľský názov vo svojich labeloch kontajnera:

```yaml
services:
  myapp:
    image: myapp:latest
    labels:
      dockflare.enable: "true"
      dockflare.hostname: "app.example.com"
      dockflare.access.group: "my-access-group"
```

Prístupová skupina `my-access-group` automaticky preloží priateľské názvy IdP na Cloudflare UUID.

---

## Osvedčené postupy

### Konvencie pomenovania

Používaj výstižné priateľské názvy:
- ✅ `google-main`, `github-dev`, `azure-work`
- ❌ `idp1`, `test`, `new`

### Bezpečnosť

- **Pravidelne rotuj secrety**: Priebežne aktualizuj client secrety
- **Obmedz rozsah**: Pri Google Workspace a Azure AD podľa možnosti obmedz na konkrétne domény
- **Otestuj pred produkciou**: IdP vždy otestuj pred uplatnením na produkčné služby
- **Sleduj používanie**: Prehodnocuj Cloudflare logy na odhalenie pokusov o neoprávnený prístup

### Viacero prostredí

Vytvor samostatných IdP pre rôzne prostredia:
- `google-dev` – vývojové prostredie
- `google-staging` – staging prostredie
- `google-prod` – produkčné prostredie

### Požiadavky na e-mail pri IdP

**DÔLEŽITÉ**: Overovanie cez IdP z bezpečnostných dôvodov vždy vyžaduje obmedzenie e-mailom.

**Príklad prístupovej skupiny:**
- **Poskytovatelia identity**: `google-main`
- **Povolené e-maily**: `admin@example.com, user@example.com, @contractor-domain.com`

Táto konfigurácia umožní prístup používateľom, ktorí:
- Sa overia cez IdP `google-main` (Google OAuth) **A**
- Majú e-mailovú adresu zodpovedajúcu jednej z: `admin@example.com`, `user@example.com` alebo ktorúkoľvek adresu `@contractor-domain.com`

**Ako to funguje:**
1. Používateľ klikne na prihlásenie vo tvojej chránenej aplikácii
2. Presmeruje sa na prihlásenie cez Google OAuth
3. Po overení cez Google Cloudflare skontroluje, či je jeho e-mail v zozname povolených
4. Prístup sa udelí len ak e-mail zodpovedá zoznamu povolených

---

## Riešenie problémov

### Chyba „Invalid Redirect URI“

**Príčina**: Redirect URI v OAuth provideri nezodpovedá URI očakávanej Cloudflare.

**Riešenie**: Uisti sa, že si pridal presnú redirect URI:
```
https://<your-team>.cloudflareaccess.com/cdn-cgi/access/callback
```
<small>Názov svojho tímu nájdeš v <a href="https://dash.cloudflare.com/{{ACCOUNT_ID}}/one/settings/custom_pages" target="_blank">Zero Trust</a> pod Settings > Custom Pages.</small>

Nahraď `<your-team>` názvom svojho Cloudflare Zero Trust tímu.

---

### „IdP Test Failed“

**Príčina**: Nesprávne prihlasovacie údaje alebo konfigurácia.

**Riešenie**:
1. Over, že Client ID a Client Secret sú správne
2. Skontroluj, že OAuth aplikácia je vo tvojom provideri zapnutá
3. Pri Azure AD over, že client ID aj tenant ID sú správne
4. Otestuj providera pomocou testovacej URL Cloudflare

---

### „Cannot Delete System-Managed IdP“

**Príčina**: Pokus o zmazanie zabudovaného providera One-Time PIN.

**Riešenie**: Provider `onetimepin` je spravovaný systémom a nedá sa zmazať. Je potrebný na overovanie cez OTP e-mailom.

---

### „IdP Not Found in Docker Label“

**Príčina**: Použitie Cloudflare UUID namiesto priateľského názvu v labeli.

**Riešenie**: V konfigurácii prístupovej skupiny použi priateľský názov (napr. `google-main`) namiesto UUID.

---

## Súvisiaca dokumentácia

- [Osvedčené postupy pre prístupové politiky](Access-Policy-Best-Practices.md)
- [Predvolené politiky zóny](Zone-Default-Policies.md)
- [Docker labely](Container-Labels.md)
- [Bezpečnostná architektúra](Security-Architecture.md)

---

## Ďalšie zdroje

- [Dokumentácia Cloudflare Zero Trust](https://developers.cloudflare.com/cloudflare-one/)
- [Špecifikácia OAuth 2.0](https://oauth.net/2/)
- [Dokumentácia OpenID Connect](https://openid.net/connect/)
