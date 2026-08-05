## Nastavenie poskytovateľa OAuth

> **📌 Dôležité:** Táto príručka je o konfigurácii **overovania webového rozhrania DockFlare** (prihlásenie do samotného DockFlare). Ak chceš nastaviť OAuth/OIDC pre **Cloudflare Access politiky** na ochranu svojich služieb, pozri radšej [Poskytovatelia identity](help/Identity-Providers.md).

DockFlare ti umožní delegovať overovanie používateľov externým providerom pomocou štandardu OpenID Connect (OIDC). Umožňuje to single sign-on (SSO) pre webové rozhranie DockFlare a integráciu s identity providermi ako Google, Authentik, Okta a ďalšími.

### Pridanie nového providera

Nového OIDC providera pridáš takto:

1.  **Prejdi do Nastavení:** Z hlavného dashboardu prejdi na stránku **Nastavenia**.
2.  **Nájdi sekciu OAuth:** Zroluj nadol do sekcie **OAuth prihlasovanie**.
3.  **Pridaj providera:** Klikni na tlačidlo **Pridať providera** a otvor konfiguračné okno.

Zobrazia sa ti tieto polia:

*   **Typ providera:** Nastavené na `OpenID Connect (OIDC)`, moderný štandard federovaného overovania.
*   **Issuer URL:** Najdôležitejšie pole. Je to základná URL tvojho OIDC providera, ktorú DockFlare použije na automatické zistenie konfigurácie providera. Napríklad `https://accounts.google.com` alebo `https://authentik.tvojadomena.com/application/o/dockflare/`.
*   **ID providera:** Krátky, jedinečný názov malými písmenami pre tohto providera (napr. `google`, `authentik-firma`). Toto ID sa používa interne a v callback URL.
*   **Zobrazovaný názov:** Používateľsky prívetivý názov, ktorý sa zobrazí na prihlasovacom tlačidle (napr. `Google`, `Firemné SSO`).
*   **Client ID:** Verejný identifikátor aplikácie DockFlare, ktorý získaš z vývojárskej konzoly svojho OIDC providera.
*   **Client Secret:** Dôverný secret aplikácie DockFlare, tiež z konzoly tvojho OIDC providera.
*   **Povoliť providera:** Toto zaškrtávacie políčko ti umožní providera kedykoľvek zapnúť alebo vypnúť.

Po vyplnení údajov klikni na **Pridať providera** a ulož.

### Nájdenie tvojej callback URL

Keď providera pridáš, potrebná **callback URL** (známa aj ako „Authorized redirect URI“) sa zobrazí pod záznamom providera na stránke Nastavenia.

Túto presnú URL musíš skopírovať a pridať do zoznamu povolených callback URL vo administrátorskej konzole svojho providera.

---

### Príklad: Nastavenie Google

Tu je stručný návod na nastavenie Google ako poskytovateľa OAuth.

1.  **Prejdi do Google Cloud Console:** Prejdi na stránku [APIs & Services > Credentials](https://console.cloud.google.com/apis/credentials).
2.  **Vytvor prihlasovacie údaje:** Klikni na **+ CREATE CREDENTIALS** a vyber **OAuth client ID**.
3.  **Nastav aplikáciu:**
    *   Nastav **Application type** na **Web application**.
    *   Daj jej názov (napr. „DockFlare“).
4.  **Pridaj Redirect URI:**
    *   Pod **Authorized redirect URIs** klikni na **+ ADD URI**.
    *   Zadaj callback URL poskytnutú DockFlare. Bude vyzerať takto: `https://tvoja-dockflare-domena.com/auth/google/callback`.
5.  **Vytvor a skopíruj:** Klikni na **CREATE**. Zobrazí sa okno s tvojím **Client ID** a **Client Secret**. Tieto hodnoty skopíruj.
6.  **Nastav v DockFlare:**
    *   **Issuer URL:** `https://accounts.google.com`
    *   **ID providera:** `google`
    *   **Zobrazovaný názov:** `Google`
    *   **Client ID:** `(Tvoje Client ID z Google)`
    *   **Client Secret:** `(Tvoj Client Secret z Google)`

Ulož providera v DockFlare a budeš sa môcť prihlásiť svojím Google účtom.

---

### Konfigurácia DockFlare s OAuth a prístupovými politikami

Pri použití OAuth overovania môžeš chcieť chrániť svoje hlavné rozhranie DockFlare prístupovými politikami a zároveň zabezpečiť, aby OAuth callbacky fungovali správne. Je to obzvlášť dôležité, ak máš na svojej inštancii DockFlare IP obmedzenia alebo iné kontroly prístupu.

#### **Osvedčený postup: Bypass politika pre OAuth callbacky**

Použi indexované labely na vytvorenie samostatných pravidiel pre hlavné rozhranie a callback cesty OAuth:

```yaml
services:
  dockflare:
    image: alplat/dockflare:stable
    labels:
      # Hlavné rozhranie DockFlare s prístupovou politikou
      - "dockflare.enable=true"
      - "dockflare.hostname=dockflare.example.com"
      - "dockflare.service=http://dockflare:5000"
      - "dockflare.access.group=team"  # tvoja vlastná prístupová politika

      # OAuth callback cesty s bypass politikou (potrebné, aby OAuth fungoval)
      - "dockflare.0.hostname=dockflare.example.com"
      - "dockflare.0.path=/auth/google/callback"
      - "dockflare.0.service=http://dockflare:5000"
      - "dockflare.0.access.policy=bypass"

      # V prípade potreby pridaj ďalšie callback cesty pre iných providerov
      - "dockflare.1.hostname=dockflare.example.com"
      - "dockflare.1.path=/auth/github/callback"
      - "dockflare.1.service=http://dockflare:5000"
      - "dockflare.1.access.policy=bypass"
```

#### **Prečo je táto konfigurácia potrebná**

- **Ochrana hlavného rozhrania**: Tvoj dashboard DockFlare zostáva chránený zvolenou prístupovou politikou
- **Funkčnosť OAuth**: OAuth callbacky sa dostanú k DockFlare bez bariér overovania
- **Bezpečnosť**: Obídu sa len konkrétne callback cesty, nie celá aplikácia
- **Flexibilita**: Funguje s ľubovoľnou kombináciou prístupových politík (na základe IP, overenia atď.)

#### **Dôležité poznámky**

1. **Zhoda ciest**: Callback cesta sa musí presne zhodovať s tým, čo očakáva tvoj OAuth provider
2. **Viacero providerov**: Pre každého poskytovateľa OAuth, ktorého nastavíš, pridaj samostatné indexované pravidlo
3. **Žiadne wildcardy**: Z bezpečnostných dôvodov sa vyhni wildcard cestám — pri callback URL buď konkrétny
4. **Testovanie**: Po konfigurácii otestuj chránený prístup (hlavné rozhranie) aj prihlasovacie toky OAuth
