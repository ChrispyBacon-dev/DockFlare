# Dostawcy tożsamości

> **📌 Ważne:** Ten przewodnik dotyczy konfigurowania **dostawców tożsamości dla zasad dostępu Cloudflare**, aby chronić Twoje usługi i aplikacje. Jeśli chcesz skonfigurować OAuth/OIDC dla **logowania do panelu administracyjnego DockFlare**, zobacz [Konfiguracja dostawcy OAuth](OAuth-Provider-Setup.md).

Dostawcy tożsamości (IdP) umożliwiają uwierzytelnianie OAuth/OIDC w aplikacjach chronionych przez Cloudflare Zero Trust. DockFlare ułatwia zarządzanie IdP i ich integrowanie z zasadami dostępu.

## Przegląd

Zamiast polegać wyłącznie na uwierzytelnianiu za pomocą poczty e-mail, możesz używać popularnych dostawców OAuth, takich jak Google, GitHub, Azure AD i inni. Użytkownicy logują się przy użyciu istniejących kont, co zapewnia wygodne i bezpieczne logowanie.

## Obsługiwani dostawcy

DockFlare obsługuje następujących dostawców tożsamości:

- **Google** - Konta Google dla użytkowników indywidualnych
- **Google Workspace** - Konta Google Workspace (G Suite) z opcjonalnym ograniczeniem domeny
- **Microsoft Azure AD** - Microsoft Entra ID (Azure Active Directory)
- **Okta** - Okta Identity Cloud
- **GitHub** - GitHub OAuth
- **Ogólny OpenID Connect** - Dowolny dostawca zgodny z OIDC

## Zarządzanie dostawcami tożsamości

### Dodawanie dostawcy tożsamości

1. Przejdź do strony **Zasady dostępu**.
2. W sekcji **Dostawcy tożsamości** kliknij **Dodaj dostawcę**.
3. Wypełnij wymagane pola:
   - **Przyjazna nazwa**: wewnętrzna nazwa w DockFlare, na przykład `google-main` lub `github-dev`
   - **Nazwa wyświetlana**: nazwa widoczna w panelu Cloudflare
   - **Typ dostawcy**: wybierz dostawcę OAuth
   - **Konfiguracja**: dane uwierzytelniające specyficzne dla danego dostawcy, zgodnie z instrukcjami poniżej
4. Kliknij **Utwórz dostawcę**.
5. Przetestuj dostawcę przy użyciu podanego testowego URL.

### Synchronizacja z Cloudflare

Jeśli masz już skonfigurowane IdP w Cloudflare Zero Trust:

1. Kliknij **Synchronizuj z Cloudflare** w sekcji Dostawcy tożsamości.
2. DockFlare zaimportuje wszystkie istniejące IdP i automatycznie wygeneruje przyjazne nazwy.
3. Możesz zmienić te nazwy, aby łatwiej używać ich w etykietach.

### Testowanie dostawcy tożsamości

Po utworzeniu IdP możesz go przetestować:

1. Kliknij menu **⋮** obok dostawcy.
2. Wybierz **Testuj IdP**.
3. Otworzy się nowe okno, w którym możesz przeprowadzić uwierzytelnienie.
4. Sprawdź, czy proces logowania działa poprawnie.

## Przewodniki konfiguracji dostawcy

### Google (konta konsumenckie)

**Krok 1: utwórz dane uwierzytelniające OAuth**

1. Przejdź do [Google Cloud Console](https://console.cloud.google.com/).
2. Utwórz nowy projekt lub wybierz istniejący.
3. Przejdź do **API i usługi** → **Poświadczenia**.
4. Kliknij **Utwórz dane uwierzytelniające** → **Identyfikator klienta OAuth**.
5. Wybierz **Aplikacja internetowa**.
6. Dodaj autoryzowany URI przekierowania:
   ```
   https://<your-team>.cloudflareaccess.com/cdn-cgi/access/callback
   ```
   <small>Nazwę swojego zespołu znajdziesz w <a href="https://one.dash.cloudflare.com/{{ACCOUNT_ID}}/settings/custom_pages" target="_blank">Zero Trust</a>, przechodząc do Ustawienia > Strony niestandardowe.</small>
7. Skopiuj **ID klienta** i **sekret klienta**.

**Krok 2: skonfiguruj w DockFlare**

- **ID klienta**: wklej wartość z Google Cloud Console
- **Sekret klienta**: wklej wartość z Google Cloud Console

---

### Google Workspace

Tak samo jak konfiguracja Google powyżej, z dodatkowym opcjonalnym polem:

- **Apps Domain**: (opcjonalnie) ogranicz do konkretnej domeny, na przykład `example.com`

Jeśli pole zostanie ustawione, uwierzytelniać będą mogli się tylko użytkownicy z adresami `@example.com`.

---

### Microsoft Azure AD

**Krok 1: zarejestruj aplikację w Azure**

1. Przejdź do [Azure Portal](https://portal.azure.com/).
2. Przejdź do **Azure Active Directory** → **Rejestracje aplikacji**.
3. Kliknij **Nowa rejestracja**.
4. Nadaj aplikacji nazwę, na przykład `DockFlare Access`.
5. W sekcji **URI przekierowania** wybierz **Web** i wpisz:
   ```
   https://<your-team>.cloudflareaccess.com/cdn-cgi/access/callback
   ```
   <small>Nazwę swojego zespołu znajdziesz w <a href="https://one.dash.cloudflare.com/{{ACCOUNT_ID}}/settings/custom_pages" target="_blank">Zero Trust</a>, przechodząc do Ustawienia > Strony niestandardowe.</small>
6. Kliknij **Zarejestruj**.
7. Skopiuj **ID aplikacji (klienta)**.
8. Skopiuj **ID katalogu (dzierżawy)**.
9. Przejdź do **Certyfikaty i sekrety** → **Nowy sekret klienta**.
10. Utwórz sekret i skopiuj **Wartość**.

**Krok 2: skonfiguruj w DockFlare**

- **ID aplikacji (klienta)**: wklej wartość z Azure
- **ID katalogu (dzierżawy)**: wklej wartość z Azure
- **Sekret klienta**: wklej wartość z Azure

---

### GitHub

**Krok 1: utwórz aplikację OAuth**

1. Przejdź do [Ustawień programisty GitHub](https://github.com/settings/developers).
2. Kliknij **Nowa aplikacja OAuth**.
3. Uzupełnij szczegóły:
   - **Nazwa aplikacji**: DockFlare Access
   - **URL strony głównej**: `https://your-domain.com`
   - **URL wywołania zwrotnego autoryzacji**:
     ```
     https://<your-team>.cloudflareaccess.com/cdn-cgi/access/callback
     ```
     <small>Nazwę swojego zespołu znajdziesz w <a href="https://one.dash.cloudflare.com/{{ACCOUNT_ID}}/settings/custom_pages" target="_blank">Zero Trust</a>, przechodząc do Ustawienia > Strony niestandardowe.</small>
4. Kliknij **Zarejestruj aplikację**.
5. Skopiuj **ID klienta**.
6. Kliknij **Wygeneruj nowy sekret klienta** i skopiuj go.

**Krok 2: skonfiguruj w DockFlare**

- **ID klienta**: wklej wartość z GitHub
- **Sekret klienta**: wklej wartość z GitHub

---

### Okta

**Krok 1: utwórz aplikację w Okta**

1. Zaloguj się do [konsoli administracyjnej Okta](https://admin.okta.com/).
2. Przejdź do **Aplikacje** → **Utwórz integrację aplikacji**.
3. Wybierz **OIDC - OpenID Connect**.
4. Wybierz **Aplikacja internetowa**.
5. Skonfiguruj:
   - **URI przekierowania logowania**:
     ```
     https://<your-team>.cloudflareaccess.com/cdn-cgi/access/callback
     ```
     <small>Nazwę swojego zespołu znajdziesz w <a href="https://one.dash.cloudflare.com/{{ACCOUNT_ID}}/settings/custom_pages" target="_blank">Zero Trust</a>, przechodząc do Ustawienia > Strony niestandardowe.</small>
6. Kliknij **Zapisz**.
7. Skopiuj **ID klienta** i **sekret klienta**.
8. Zanotuj swoją **domenę Okta**, na przykład `https://dev-12345.okta.com`.

**Krok 2: skonfiguruj w DockFlare**

- **URL konta Okta**: Twoja domena Okta, na przykład `https://dev-12345.okta.com`
- **ID klienta**: wklej wartość z Okta
- **Sekret klienta**: wklej wartość z Okta

---

### Ogólny OpenID Connect

Dla dowolnego dostawcy zgodnego z OIDC:

**Krok 1: pobierz konfigurację dostawcy**

Z dokumentacji dostawcy tożsamości pobierz:
- URL autoryzacji
- URL tokena
- URL JWKS (JSON Web Key Set)
- ID klienta
- Sekret klienta

**Krok 2: skonfiguruj w DockFlare**

- **URL autoryzacji**: endpoint autoryzacji OAuth dostawcy
- **URL tokena**: endpoint tokena dostawcy
- **URL JWKS**: endpoint JWKS dostawcy używany do weryfikacji podpisu
- **ID klienta**: wartość od dostawcy
- **Sekret klienta**: wartość od dostawcy

---

## Używanie dostawców tożsamości w zasadach dostępu

### W grupach dostępu

1. Przejdź do **Zasady dostępu** → **Zaawansowane zasady dostępu**.
2. Kliknij **Utwórz nową grupę** lub edytuj istniejącą grupę.
3. W sekcji **Reguły polityki**:
   - **Dostawcy tożsamości**: wybierz jeden lub więcej IdP
   - **Dozwolone adresy e-mail lub domeny**: **wymagane przy użyciu IdP**. Określ dozwolone adresy e-mail.
4. Zapisz grupę.

### Tryby uwierzytelniania

Masz dwie opcje:

1. **Tylko e-mail**: wpisz adresy e-mail i nie wybieraj żadnego IdP. Użytkownicy uwierzytelniają się jednorazowym PIN-em.
2. **IdP + e-mail (wymagane)**: wybierz IdP i wpisz dozwolone adresy e-mail. Użytkownicy muszą uwierzytelnić się przez wybranego dostawcę tożsamości i znajdować się na liście dozwolonych adresów.

**⚠️ Uwaga dotycząca bezpieczeństwa:** przy korzystaniu z dostawców tożsamości **musisz** określić dozwolone adresy e-mail. Zapobiega to nieautoryzowanemu dostępowi. Na przykład bez ograniczeń adresów e-mail wybranie `Google` jako IdP pozwoliłoby na dostęp każdemu użytkownikowi z kontem Google.

### W etykietach Dockera

Użyj przyjaznej nazwy w etykietach kontenera:

```yaml
services:
  myapp:
    image: myapp:latest
    labels:
      dockflare.enable: "true"
      dockflare.hostname: "app.example.com"
      dockflare.access.group: "my-access-group"
```

Grupa dostępu `my-access-group` automatycznie przetłumaczy przyjazne nazwy IdP na identyfikatory UUID Cloudflare.

---

## Najlepsze praktyki

### Konwencje nazewnictwa

Używaj opisowych i czytelnych nazw:
- ✅ `google-main`, `github-dev`, `azure-work`
- ❌ `idp1`, `test`, `new`

### Bezpieczeństwo

- **Regularnie rotuj sekrety**: okresowo aktualizuj sekrety klienta
- **Ogranicz zakres**: w przypadku Google Workspace i Azure AD ograniczaj dostęp do konkretnych domen, jeśli to możliwe
- **Testuj przed wdrożeniem produkcyjnym**: zawsze przetestuj IdP przed użyciem w usługach produkcyjnych
- **Monitoruj użycie**: przeglądaj logi Cloudflare, aby wykrywać próby nieautoryzowanego dostępu

### Wiele środowisk

Twórz osobne IdP dla różnych środowisk:
- `google-dev` - Środowisko deweloperskie
- `google-staging` - Środowisko testowe
- `google-prod` - Środowisko produkcyjne

### Wymagania dotyczące e-maili przy IdP

**WAŻNE:** uwierzytelnianie przez IdP zawsze wymaga ograniczeń adresów e-mail ze względów bezpieczeństwa.

**Przykładowa grupa dostępu:**
- **Dostawcy tożsamości**: `google-main`
- **Dozwolone adresy e-mail**: `admin@example.com, user@example.com, @contractor-domain.com`

Ta konfiguracja daje dostęp użytkownikom, którzy:
- Uwierzytelniają się przez IdP `google-main` (Google OAuth) **ORAZ**
- Mają adres e-mail zgodny z `admin@example.com`, `user@example.com` lub dowolnym adresem `@contractor-domain.com`

**Jak to działa:**
1. Użytkownik klika logowanie w chronionej aplikacji.
2. Zostaje przekierowany do logowania Google OAuth.
3. Po uwierzytelnieniu Cloudflare sprawdza, czy adres e-mail znajduje się na liście dozwolonych.
4. Dostęp zostaje przyznany tylko wtedy, gdy adres e-mail pasuje do listy.

---

## Rozwiązywanie problemów

### Błąd „Nieprawidłowy URI przekierowania”

**Przyczyna**: URI przekierowania ustawiony u dostawcy OAuth nie zgadza się z oczekiwanym URI Cloudflare.

**Rozwiązanie**: upewnij się, że dodano dokładnie ten URI:
```
https://<your-team>.cloudflareaccess.com/cdn-cgi/access/callback
```
<small>Nazwę swojego zespołu znajdziesz w <a href="https://one.dash.cloudflare.com/{{ACCOUNT_ID}}/settings/custom_pages" target="_blank">Zero Trust</a>, przechodząc do Ustawienia > Strony niestandardowe.</small>

Zastąp `<your-team>` nazwą zespołu Cloudflare Zero Trust.

---

### „Test IdP nie powiódł się”

**Przyczyna**: nieprawidłowe dane uwierzytelniające lub błędna konfiguracja.

**Rozwiązanie**:
1. Sprawdź, czy ID klienta i sekret klienta są poprawne.
2. Upewnij się, że aplikacja OAuth jest włączona u dostawcy.
3. W przypadku Azure AD sprawdź zarówno ID klienta, jak i ID tenant.
4. Przetestuj dostawcę, używając testowego URL-a Cloudflare.

---

### „Nie można usunąć IdP zarządzanego przez system”

**Przyczyna**: próbujesz usunąć wbudowanego dostawcę One-Time PIN.

**Rozwiązanie**: dostawca `onetimepin` jest zarządzany przez system i nie można go usunąć. Jest wymagany do uwierzytelniania OTP opartego na e-mailu.

---

### „Nie znaleziono IdP w etykiecie Dockera”

**Przyczyna**: w etykiecie użyto UUID Cloudflare zamiast przyjaznej nazwy.

**Rozwiązanie**: użyj przyjaznej nazwy, na przykład `google-main`, zamiast UUID w konfiguracji grupy dostępu.

---

## Powiązana dokumentacja

- [Najlepsze praktyki dla zasad dostępu](Access-Policy-Best-Practices.md)
- [Domyślne zasady strefy](Zone-Default-Policies.md)
- [Etykiety kontenerów](Container-Labels.md)
- [Architektura bezpieczeństwa](Security-Architecture.md)

---
