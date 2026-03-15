# Domyślne zasady strefy — ochrona przed symbolami wieloznacznymi

## Przegląd

Domyślne zasady strefy to najlepsza praktyka w zakresie bezpieczeństwa, która wykorzystuje aplikacje wieloznaczne Cloudflare Access (`*.domain.com`) do automatycznej ochrony wszystkich subdomen strefy DNS.

## Problem, który to rozwiązuje

Bez domyślnych zasad strefy:
- Zapomniane usługi są ujawniane publicznie
- Nowe subdomeny nie są chronione, dopóki nie zostaną ręcznie skonfigurowane
- Literówki w konfiguracjach nazw hostów omijają kontrolę dostępu
- Dryfowanie dokumentacji prowadzi do luk w zabezpieczeniach

## Jak to działa

### Priorytet polityki

Cloudflare ocenia zasady dostępu w następującej kolejności:

1. **Dokładne dopasowanie nazwy hosta** (np. `app.example.com`)
2. **Dopasowanie symboli wieloznacznych** (np. `*.example.com`)
3. **Brak dopasowania** = Dostęp publiczny (bez aplikacji Access)

### Implementacja DockFlare

Sekcja **Domyślne zasady strefy** DockFlare:
- Wyświetla listę wszystkich stref DNS Cloudflare
- Pokazuje stan ochrony za pomocą plakietek wizualnych
- Umożliwia tworzenie polityk `*.zone.com` jednym kliknięciem
- Pozwala wybrać, która grupa dostępu chroni strefę

## Przewodnik konfiguracji

### Krok 1: Przejrzyj swoje strefy

1. Przejdź do strony **Zasady dostępu**
2. Przewiń do **Domyślne zasady strefy (*.tld Wildcards)**
3. Sprawdź stan ochrony:
   - 🛡️ **Zielony „Chroniony”** - W strefie obowiązują zasady dotyczące symboli wieloznacznych
   - ⚠️ **Żółty „Niechroniony”** – Strefa jest zagrożona

### Krok 2: Utwórz zasady dotyczące stref

Dla każdej strefy niechronionej:

1. Kliknij przycisk **Utwórz politykę**
2. Okno modalne pokazuje nazwę hosta `*.zone-name.com`
3. Wybierz odpowiednią Politykę dostępu:
   - **Strefy publiczne** → `public-default-bypass`
   - **Strefy wewnętrzne** → Polityka uwierzytelniania
   - **Strefy mieszane** → Najbardziej restrykcyjna polityka
4. Kliknij **Utwórz politykę strefową**

### Krok 3: Zweryfikuj w Cloudflare

1. Otwórz pulpit nawigacyjny Cloudflare Zero Trust
2. Przejdź do Access → Applications
3. Poszukaj aplikacji o nazwie `Zone Default: *.domain.com`
4. Sprawdź, czy polityka jest poprawna

## Zalecenia dotyczące bezpieczeństwa

### Środowiska produkcyjne

✅ **Zawsze włączaj domyślne zasady strefy**
- Zapobiega przypadkowemu narażeniu
- Wychwytuje błędy konfiguracyjne
- Chroni przed atakami polegającymi na odkrywaniu subdomen

### Strategia wyboru polityki

- **Domeny treści publicznych** (blogi, marketing): `public-default-bypass`
- **Domeny narzędzi wewnętrznych**: Uwierzytelnianie poczty/domeny
- **Wrażliwe domeny danych**: uwierzytelnianie z włączoną obsługą MFA
- **Domeny programistyczne**: Blokuj według najsurowszych zasad

### Monitorowanie

Regularnie przeglądaj:
- Które strefy są objęte ochroną (strona **Zasady dostępu**)
- Uzyskaj dostęp do dzienników aplikacji w Cloudflare
- Lista aktywnych subdomen vs skonfigurowane zasady

## Rozwiązywanie problemów

### Błąd „Zasady już istnieją”.

Aplikacja dostępu `*.domain.com` już istnieje. Może to być:
- Utworzono ręcznie w Cloudflare
- Utworzony wcześniej przez DockFlare
- Utworzony przez inne narzędzie

**Rozwiązanie:** Zarządzaj nim bezpośrednio w Cloudflare lub usuń i utwórz ponownie za pomocą DockFlare.

### Usługa nadal dostępna bez uwierzytelnienia

Sprawdź priorytet polityki:
1. Sprawdź, czy usługa ma określone zasady dotyczące nazw hostów
2. Sprawdź, czy istnieje symbol wieloznaczny strefy i czy jest on poprawnie skonfigurowany
3. Jeżeli mimo ochrony strefy usługa ma być publiczna, dodaj etykietę `dockflare.access.group=public-default-bypass`

### Omijanie ochrony strefowej dla usług publicznych

Jeśli masz politykę uwierzytelniania na poziomie strefy, ale potrzebujesz określonych usług, aby pozostały publiczne:

1. Dodaj etykietę obejściową do kontenera:
   ```yaml
   labels:
     - "dockflare.access.group=public-default-bypass"
   ```
2. Spowoduje to utworzenie aplikacji dostępu o dokładnej nazwie hosta z decyzją o pominięciu
3. Zasady dotyczące dokładnych nazw hostów zastępują zasady dotyczące symboli wieloznacznych
4. Serwis staje się publicznie dostępny, a strefa pozostaje chroniona

Następnie:
- Sprawdź dzienniki dostępu Cloudflare, aby potwierdzić kolejność oceny polityk.
- Upewnij się, że rekordy DNS wskazują poprawny tunel.

### Strefa nie jest wyświetlana na liście

Możliwe przyczyny:
- Strefa DNS nie znajduje się na Twoim koncie Cloudflare
- Token API nie ma uprawnienia `Zone:Zone:Read`
- Strefa jest wstrzymana lub usunięta

**Rozwiązanie:** Sprawdź, czy strefa istnieje w panelu Cloudflare i czy token API ma prawidłowe uprawnienia.

## Najlepsze praktyki

1. **Najpierw utwórz zasady strefy** – Przed dodaniem usług
2. **Użyj uwierzytelniania dla stref wewnętrznych** - Nigdy nie używaj obejścia
3. **Udokumentuj wyjątki** — jeśli strefa nie wymaga ochrony, udokumentuj dlaczego
4. **Regularne audyty** - Comiesięczny przegląd stanu ochrony strefy
5. **Test przed rozpoczęciem produkcji** — Sprawdź, czy zasady dotyczące symboli wieloznacznych nie zakłócają istniejących usług
6. **Zasada najmniejszych uprawnień** – Stosuj najbardziej restrykcyjne zasady, które nadal umożliwiają legalny dostęp

## Przykładowe konfiguracje

### Strefa Blogów Publicznych
```
Zone: blog.example.com
Policy: public-default-bypass
Result: All subdomains publicly accessible (*.blog.example.com)
```

### Wewnętrzna Strefa Narzędzi
```
Zone: internal.company.com
Policy: Company Email Authentication
Result: All subdomains require @company.com email (*.internal.company.com)
```

### Mieszana Strefa Rozwoju
```
Zone: dev.company.com
Policy: Developer Team Authentication
Result: All dev services protected by default (*.dev.company.com)
Specific overrides: public-demo.dev.company.com → public-default-bypass
```

## Zrozumienie priorytetu polityki

### Scenariusz 1: Określona zasada zastępuje symbol wieloznaczny

**Konfiguracja:**
- Polityka dotycząca strefy: `*.example.com` → Wymaga uwierzytelnienia
- Szczegółowe zasady: `blog.example.com` → `public-default-bypass`

**Wynik:**
- `blog.example.com` → Publiczny (wygrywa konkretna polityka)
- `api.example.com` → Wymaga uwierzytelnienia (przechwytuje go symbol wieloznaczny)
- `forgotten.example.com` → Wymaga uwierzytelnienia (przechwytuje go symbol wieloznaczny)

### Scenariusz 2: Dzika karta jako siatka bezpieczeństwa

**Konfiguracja:**
- Zasady dotyczące strefy: `*.internal.company.com` → Wymaga adresu e-mail @company.com
- Szczegółowe zasady: brak dla `test-server.internal.company.com`

**Wynik:**
- `test-server.internal.company.com` → Wymaga uwierzytelnienia (chroni je symbol wieloznaczny)
- Nawet jeśli zapomniałeś go skonfigurować, polityka strefy chroni go

### Scenariusz 3: Brak ochrony

**Konfiguracja:**
- Polityka dotycząca stref: Brak dla `*.risky-domain.com`
- Szczegółowe zasady: `app.risky-domain.com` → Uwierzytelnianie

**Wynik:**
- `app.risky-domain.com` → Wymaga autoryzacji (konkretne zasady)
- `forgotten.risky-domain.com` → ⚠️ **PUBLICZNE** (nie ma symbolu wieloznacznego, który mógłby to złapać)

## Integracja z etykietami DockFlare

### Używanie etykiety `default_tld`

Etykieta `dockflare.access.policy=default_tld` informuje DockFlare, aby używał zasad wieloznacznych strefy:

```yaml
services:
  my-service:
    image: nginx
    labels:
      - "dockflare.enable=true"
      - "dockflare.hostname=new-app.internal.company.com"
      - "dockflare.service=http://my-service:80"
      - "dockflare.access.policy=default_tld"
```

**Zachowanie:**
- Jeśli istnieje `*.internal.company.com` → Dziedziczy tę politykę
- Jeśli nie istnieje żadna polityka strefy → Usługa jest publiczna (nie utworzono aplikacji Access)

### Zalecenie

Zamiast polegać na etykiecie `default_tld`:
1. Utwórz domyślne zasady strefy w interfejsie użytkownika
2. Pozwól, aby polityka wieloznaczna automatycznie chroniła wszystkie usługi
3. Twórz tylko określone zasady dla wyjątków

Zapewnia to domyślnie większe bezpieczeństwo.

## Powiązana dokumentacja

- [Sprawdzone praktyki dotyczące zasad dostępu](Access-Policy-Best-Practices.md)
- [Korzystanie z panelu administracyjnego](Using-the-Web-UI.md)
- [Etykiety kontenerów](Container-Labels.md)
- [Jak działa DockFlare](How-DockFlare-Works.md)
- [Architektura bezpieczeństwa](Security-Architecture.md)
