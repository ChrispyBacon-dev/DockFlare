## Konfiguracja dostawcy OAuth

> **📌 Ważne:** Ten przewodnik dotyczy konfiguracji **uwierzytelniania panelu administracyjnego DockFlare** (czyli logowania do samego DockFlare). Jeśli chcesz skonfigurować OAuth/OIDC dla **zasad dostępu Cloudflare** w celu ochrony swoich usług, zobacz [Dostawcy tożsamości](Identity-Providers.md).

DockFlare pozwala przekazać uwierzytelnianie użytkowników zewnętrznym dostawcom przy użyciu standardu OpenID Connect (OIDC). Dzięki temu możesz włączyć jednokrotne logowanie (SSO) do panelu administracyjnego DockFlare i zintegrować się z dostawcami tożsamości, takimi jak Google, Authentik czy Okta.

### Dodawanie nowego dostawcy

Wykonaj poniższe kroki, aby dodać nowego dostawcę OIDC:

1. **Przejdź do Ustawień:** W głównym panelu otwórz stronę **Ustawienia**.
2. **Znajdź sekcję OAuth:** Przewiń do sekcji **Uwierzytelnianie OAuth**.
3. **Dodaj dostawcę:** Kliknij przycisk **Dodaj dostawcę**, aby otworzyć formularz konfiguracji.

Zostaną wyświetlone następujące pola:

* **Typ dostawcy:** Jest ustawiony na `OpenID Connect (OIDC)`, czyli nowoczesny standard uwierzytelniania federacyjnego.
* **Adres URL wydawcy:** To najważniejsze pole. Jest to bazowy adres URL dostawcy OIDC, którego DockFlare używa do automatycznego wykrywania konfiguracji. Na przykład `https://accounts.google.com` lub `https://authentik.yourdomain.com/application/o/dockflare/`.
* **Identyfikator dostawcy:** Krótka, unikalna nazwa zapisana małymi literami (np. `google`, `authentik-corp`). Ten identyfikator jest używany wewnętrznie oraz w adresie URL callbacku.
* **Nazwa wyświetlana:** Nazwa widoczna na przycisku logowania (np. `Google`, `Corporate SSO`).
* **Identyfikator klienta:** Publiczny identyfikator aplikacji DockFlare, który otrzymasz w konsoli deweloperskiej swojego dostawcy OIDC.
* **Sekret klienta:** Poufny sekret aplikacji DockFlare, również pobierany z konsoli Twojego dostawcy OIDC.
* **Włącz dostawcę:** To pole wyboru pozwala w dowolnym momencie włączyć lub wyłączyć dostawcę.

Po uzupełnieniu pól kliknij **Dodaj dostawcę**, aby zapisać konfigurację.

### Sprawdzenie URL callbacku

Po dodaniu dostawcy wymagany **URL callbacku** (znany również jako „autoryzowany URI przekierowania”) zostanie wyświetlony pod wpisem dostawcy na stronie Ustawienia.

Musisz skopiować dokładnie ten URL i dodać go do listy dozwolonych adresów callbacku w konsoli administracyjnej dostawcy.

---

### Przykład: konfiguracja Google

Poniżej szybki przykład konfiguracji Google jako dostawcy OAuth.

1. **Przejdź do Google Cloud Console:** Otwórz stronę [API i usługi > Dane uwierzytelniające](https://console.cloud.google.com/apis/credentials).
2. **Utwórz dane uwierzytelniające:** Kliknij **+ UTWÓRZ POŚWIADCZENIA** i wybierz **Identyfikator klienta OAuth**.
3. **Skonfiguruj aplikację:**
    * Ustaw **Typ aplikacji** na **Aplikacja internetowa**.
    * Nadaj jej nazwę, na przykład „DockFlare”.
4. **Dodaj URI przekierowania:**
    * W obszarze **URI autoryzowanych przekierowań** kliknij **+ DODAJ URI**.
    * Wprowadź adres URL callbacku podany przez DockFlare. Będzie wyglądał na przykład tak: `https://your-dockflare-domain.com/auth/google/callback`.
5. **Utwórz i skopiuj:** Kliknij **UTWÓRZ**. Pojawi się okno z **Identyfikatorem klienta** i **Sekretem klienta**. Skopiuj te wartości.
6. **Skonfiguruj w DockFlare:**
    * **URL wydawcy:** `https://accounts.google.com`
    * **Identyfikator dostawcy:** `google`
    * **Nazwa wyświetlana:** `Google`
    * **Identyfikator klienta:** `(Your Client ID from Google)`
    * **Sekret klienta:** `(Your Client Secret from Google)`

Zapisz dostawcę w DockFlare, a następnie zaloguj się za pomocą konta Google.

---

### Konfiguracja DockFlare z OAuth i zasadami dostępu

Jeśli korzystasz z uwierzytelniania OAuth, możesz chcieć chronić główny interfejs DockFlare za pomocą zasad dostępu, a jednocześnie zapewnić poprawne działanie callbacków OAuth. Jest to szczególnie ważne, gdy Twoja instancja DockFlare ma ograniczenia IP lub inne mechanizmy kontroli dostępu.

#### **Dobra praktyka: polityka bypass dla callbacków OAuth**

Użyj indeksowanych etykiet, aby utworzyć osobne reguły dla głównego interfejsu i ścieżek callbacków OAuth:

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

#### **Dlaczego ta konfiguracja jest potrzebna**

- **Ochrona głównego interfejsu**: panel DockFlare pozostaje zabezpieczony wybraną polityką dostępu.
- **Działanie OAuth**: callbacki OAuth mogą dotrzeć do DockFlare bez blokady na warstwie uwierzytelniania.
- **Bezpieczeństwo**: omijane są tylko konkretne ścieżki callbacków, a nie cała aplikacja.
- **Elastyczność**: rozwiązanie działa z dowolną kombinacją polityk dostępu, na przykład opartych na IP lub uwierzytelnianiu.

#### **Ważne uwagi**

1. **Dokładne dopasowanie ścieżki**: ścieżka callbacku musi dokładnie odpowiadać temu, czego oczekuje dostawca OAuth.
2. **Wielu dostawców**: dodaj osobną indeksowaną regułę dla każdego skonfigurowanego dostawcy OAuth.
3. **Bez symboli wieloznacznych**: ze względów bezpieczeństwa unikaj ścieżek z wildcardami i używaj konkretnych adresów URL callbacków.
4. **Testy**: po konfiguracji sprawdź zarówno chroniony dostęp do głównego interfejsu, jak i przepływy logowania OAuth.
