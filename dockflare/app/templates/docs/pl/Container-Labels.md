# Odniesienie do etykiet kontenerów

DockFlare konfiguruje się głównie za pomocą etykiet Dockera dołączonych do kontenerów. Ta strona zawiera wyczerpujące informacje na temat wszystkich obsługiwanych etykiet.

## Konfiguracja podstawowa

Etykiety te kontrolują podstawową definicję routingu i usługi dla kontenera.

| Etykieta | Opis | Przykład |
| :--- | :--- | :--- |
| `dockflare.enable` | **Wymagane.** Wyłącznik główny. Musi być ustawiony na `true`, aby DockFlare mógł zarządzać kontenerem. | `dockflare.enable=true` |
| `dockflare.hostname` | **Wymagane.** Publiczna nazwa hosta Twojej usługi. | `dockflare.hostname=myservice.example.com` |
| `dockflare.service` | **Wymagane.** Wewnętrzny adres URL usługi, z którą Cloudflare Tunnel powinien się połączyć. Może mieć wartość `http`, `https`, `tcp`, `ssh`, `rdp`, `http_status:XXX` lub `bastion`. | `dockflare.service=http://my-app-container:8080` |
| `dockflare.path` | Ścieżka URL prowadząca do tej usługi. Przydatne do eksponowania wielu usług pod tą samą nazwą hosta. | `dockflare.path=/api` |
| `dockflare.zonename` | (Opcjonalnie) Jawna strefa Cloudflare (domena), w której powinien zostać utworzony rekord DNS. Jeśli zostanie pominięty, DockFlare automatycznie wykrywa strefę na podstawie nazwy hosta i powraca do skonfigurowanej wartości domyślnej (`CF_ZONE_ID`), gdy automatyczne wykrywanie nie powiedzie się. | `dockflare.zonename=another-domain.com` |
| `dockflare.no_tls_verify` | Jeśli ustawione na `true`, wyłącza weryfikację certyfikatu TLS dla połączenia między `cloudflared` a usługą Origin. Przydatne w przypadku źródeł z certyfikatami z podpisem własnym. | `dockflare.no_tls_verify=true` |
| `dockflare.originsrvname` | Ustawia konkretną nazwę hosta Server Name Indication (SNI) dla połączenia TLS ze źródłem. Na panelu kontrolnym Cloudflare jest to również znane jako „Nazwa serwera początkowego”. | `dockflare.originsrvname=internal.service.local` |
| `dockflare.httpHostHeader` | Zastępuje nagłówek `Host` wysłany z `cloudflared` do usługi Origin. | `dockflare.httpHostHeader=custom-host.internal` |
| `dockflare.http2_origin` | Jeśli ustawione na `true`, włącza protokół HTTP/2 dla połączenia między `cloudflared` a usługą Origin. Wymagane w przypadku usług gRPC. Dotyczy tylko usług HTTP/HTTPS. | `dockflare.http2_origin=true` |
| `dockflare.disable_chunked_encoding` | Jeśli ustawione na `true`, wyłącza kodowanie transferu fragmentarycznego przez HTTP/1.1. Przydatne dla serwerów WSGI (Flask, Django, FastAPI) i innych źródeł, które nie obsługują poprawnie żądań fragmentarycznych. Dotyczy tylko usług HTTP/HTTPS. | `dockflare.disable_chunked_encoding=true` |

> **Wskazówka:** Począwszy od DockFlare v3.0 możesz pominąć `dockflare.zonename` w przypadku większości workloadów. Master wykrywa poprawną strefę Cloudflare, dopasowując sufiks nazwy hosta i wraca do skonfigurowanej strefy domyślnej tylko wtedy, gdy nie może znaleźć dopasowania. Podaj etykietę tylko wtedy, gdy chcesz celowo utworzyć rekord w innej strefie.

> **Uwaga:** Opcja **Dopasuj SNI do hosta** w Cloudflare jest dostępna w ręcznej konfiguracji reguł DockFlare na pulpicie nawigacyjnym. Obecnie nie jest ustawiana za pomocą etykiety platformy Docker.

---

## Konfiguracja zasad dostępu

Etykiety te umożliwiają dynamiczne tworzenie aplikacji Cloudflare Access i zarządzanie nimi w celu zabezpieczenia usług.

**Uwaga:** Zdecydowanie zaleca się używanie **Grup dostępu** (`dockflare.access.group`) do zarządzania politykami. DockFlare 3.0.3 synchronizuje każdą grupę dostępu z nazwaną polityką dostępu Cloudflare wielokrotnego użytku, umożliwiając wielokrotne wykorzystanie i dwukierunkową edycję. Korzystanie z indywidualnych etykiet najlepiej sprawdza się w przypadku jednorazowych, niepowtarzalnych konfiguracji. Jeśli użyto `dockflare.access.group` lub `dockflare.access.groups`, wszystkie pozostałe etykiety `dockflare.access.*` są ignorowane.

### Ważne zmiany w wersji 3.0.3

#### Domyślna zasada obejścia systemu

Począwszy od wersji 3.0.3, jeśli użyjesz `dockflare.access.policy=bypass` lub `dockflare.access.group=bypass`, Twoja usługa będzie odwoływać się do zarządzanych przez system zasad wielokrotnego użytku `public-default-bypass` zamiast tworzyć zasady wbudowane. Dzięki temu pulpit nawigacyjny Cloudflare będzie czysty.

- **Przed wersją 3.0.3:** Każda reguła obejścia tworzyła osobną politykę inline
- **v3.0.3+:** Wszystkie reguły obejścia mają wspólną jedną kanoniczną zasadę `public-default-bypass`

#### Migracja starszych etykiet

DockFlare automatycznie migruje starsze etykiety obejścia, aby korzystać ze scentralizowanych zasad systemu:

- `dockflare.access.policy=bypass` → Używa polityki systemowej `public-default-bypass`
- `dockflare.access.group=bypass` → Używa polityki systemowej `public-default-bypass`

Migracja odbywa się w sposób przejrzysty podczas przetwarzania i uzgadniania kontenerów. Twoje kontenery będą nadal działać bez konieczności wprowadzania jakichkolwiek zmian.

#### Uproszczona konfiguracja dostępu

W przypadku złożonych scenariuszy dostępu (uwierzytelnianie poczty e-mail/domeny, umieszczanie na białej liście adresów IP itp.) zaleca się obecnie:

1. Utwórz grupę dostępu na stronie **Zasady dostępu**
2. Odwołaj się do niego za pomocą `dockflare.access.group=your-group-id`

Opcje szybkiego tworzenia zostały usunięte z interfejsu użytkownika, aby zachęcić do stosowania najlepszych praktyk.

#### Etykieta domyślnych zasad strefy

Etykieta `dockflare.access.policy=default_tld` nadal działa i będzie dziedziczyć ochronę z zasad wieloznacznych `*.domain.com` Twojej strefy. Jeśli nie istnieje żadna polityka strefy, usługa będzie publiczna (bez aplikacji Access).

**Zalecenie:** Utwórz domyślne zasady strefy dla wszystkich swoich domen w interfejsie użytkownika, aby zapewnić większe bezpieczeństwo.

| Etykieta | Opis | Przykład |
| :--- | :--- | :--- |
| `dockflare.access.group` | Identyfikator pojedynczej, wcześniej skonfigurowanej grupy dostępu, która ma zostać zastosowana do tej usługi. Identyfikator znajdziesz na stronie „Zasady dostępu” w panelu DockFlare. | `dockflare.access.group=internal-tools-policy` |
| `dockflare.access.groups` | Rozdzielana przecinkami lista identyfikatorów grup dostępu do zastosowania. Umożliwia to nałożenie wielu zasad na jedną usługę. | `dockflare.access.groups=allow-team-a,allow-admins` |
| `dockflare.access.policy` | Podstawowy typ zasad. Może mieć wartość `bypass` (publiczny), `authenticate` (wymaga logowania) lub `default_tld` (dziedziczy z zasady `*.domain.com`). Jeśli nieskonfigurowana, usługa będzie publiczna. Preferuj grupy dostępu dla polityk wielokrotnego użytku; te etykiety służą do specjalistycznych zastąpień. | `dockflare.access.policy=authenticate` |
| `dockflare.access.name` | Niestandardowa nazwa aplikacji dostępowej Cloudflare. Wartość domyślna to `DockFlare-{hostname}`. | `dockflare.access.name=My Web App Access` |
| `dockflare.access.session_duration` | Czas trwania sesji uwierzytelnionych użytkowników (np. `24h`, `30m`). Wartość domyślna to `24h`. | `dockflare.access.session_duration=1h` |
| `dockflare.access.app_launcher_visible` | Jeśli `true`, aplikacja będzie widoczna w App Launcherze Cloudflare Access. | `dockflare.access.app_launcher_visible=true` |
| `dockflare.access.allowed_idps` | Rozdzielana przecinkami lista dozwolonych identyfikatorów UUID dostawcy tożsamości (IdP). Znajdziesz je na pulpicie nawigacyjnym Cloudflare Zero Trust. | `dockflare.access.allowed_idps=uuid1,uuid2` |
| `dockflare.access.auto_redirect_to_identity` | Jeśli `true`, użytkownicy zostaną natychmiast przekierowani na stronę logowania dostawcy tożsamości zamiast na stronę powitalną Cloudflare Access. | `dockflare.access.auto_redirect_to_identity=true` |
| `dockflare.access.custom_rules` | Ciąg JSON reprezentujący tablicę reguł zasad dostępu Cloudflare. Zapewnia to maksymalną elastyczność w przypadku złożonych, jednorazowych polis. | `dockflare.access.custom_rules='[{"email":{"email":"user@example.com"},"action":"allow"}]'` |

---

## Indeksowane etykiety dla wielu domen

DockFlare obsługuje definiowanie wielu nazw hostów dla pojedynczego kontenera przy użyciu indeksowanych etykiet. Jest to przydatne do ujawniania różnych portów lub ścieżek tej samej usługi na różnych publicznych nazwach hostów.

Aby użyć etykiet indeksowanych, poprzedź etykietę liczbą całkowitą, zaczynając od `0`.

* Zawsze wymagana jest indeksowana nazwa hosta (`<index>.hostname`).
* Inne etykiety o tym samym indeksie (np. `<index>.service`, `<index>.path`) zastąpią podstawowe (nieindeksowane) etykiety dla tej konkretnej nazwy hosta.
* Jeśli etykieta indeksowana nie zostanie dostarczona, wartość zostanie przywrócona do wartości odpowiadającej etykiecie bazowej.

### Przykład

Ten przykład przedstawia dwie nazwy hostów z jednego kontenera:
1. `app.example.com` kieruje do głównego interfejsu WWW na porcie `80`.
2. `api.example.com` kieruje do API na porcie `3000` i jest zabezpieczony określoną grupą dostępu.

```yaml
services:
  my-multi-service:
    image: my-app
    labels:
      - "dockflare.enable=true"

      # --- Definition 0 ---
      - "dockflare.0.hostname=app.example.com"
      - "dockflare.0.service=http://my-multi-service:80"

      # --- Definition 1 ---
      - "dockflare.1.hostname=api.example.com"
      - "dockflare.1.service=http://my-multi-service:3000"
      - "dockflare.1.access.group=api-access-policy"
```
