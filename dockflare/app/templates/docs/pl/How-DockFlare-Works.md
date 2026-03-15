# Jak działa DockFlare

DockFlare działa jako pomost między środowiskiem Docker a siecią Cloudflare, automatyzując bezpieczne wystawianie usług do Internetu. Stale monitoruje host Dockera i wykorzystuje API Cloudflare do zarządzania tunelami, rekordami DNS oraz zasadami dostępu w Twoim imieniu.

## Główny przepływ pracy

Podstawowy przepływ działania można podzielić na kilka kroków:

1. **Monitorowanie zdarzeń Dockera**: DockFlare nasłuchuje zdarzeń z gniazda Dockera, takich jak `start` i `stop` kontenerów.

2. **Wykrywanie etykiet**: gdy uruchamia się nowy kontener, DockFlare sprawdza, czy ma etykiety `dockflare.`. Jeśli znajdzie `dockflare.enable=true`, wie, że ma zarządzać tym kontenerem.

3. **Komunikacja z API Cloudflare**: na podstawie etykiet DockFlare konfiguruje w Cloudflare potrzebne zasoby:
   * **Cloudflare Tunnel**: dodaje regułę ingress do wybranego tunelu Cloudflare. Reguła kieruje publiczną nazwę hosta na wewnętrzny adres kontenera, na przykład `http://my-app:8080`.
   * **Zarządzanie DNS**: tworzy rekord DNS CNAME w strefie Cloudflare i wskazuje żądaną publiczną nazwę hosta, na przykład `my-app.example.com`, na tunel Cloudflare.
   * **Zasady dostępu**: jeśli zdefiniowano etykiety kontroli dostępu, DockFlare tworzy lub aktualizuje wielokrotnego użytku politykę Cloudflare Access, aby zabezpieczyć usługę regułami Zero Trust, na przykład wymagając logowania przez dostawcę tożsamości albo ustawiając publiczny `bypass`.

4. **Automatyczne czyszczenie**: gdy zarządzany kontener zostanie zatrzymany lub usunięty, DockFlare automatycznie uruchamia proces porządkowania. Usuwa odpowiadającą regułę ingress z tunelu Cloudflare, a jeśli żaden inny serwis nie używa danej nazwy hosta, usuwa również rekord DNS oraz aplikację Access. Dzięki temu konfiguracja Cloudflare pozostaje spójna i wolna od przestarzałych wpisów.

## Komponenty w skrócie

| Składnik | Odpowiedzialność |
| --- | --- |
| DockFlare Master | Udostępnia panel administracyjny i API, obserwuje zdarzenia Dockera oraz orkiestruje tunele Cloudflare, DNS i zasady dostępu. Działa bez uprawnień roota i komunikuje się z Dockerem wyłącznie przez socket proxy. |
| Docker Socket Proxy | Sidecar `tecnativa/docker-socket-proxy`, który udostępnia Masterowi minimalny zakres Docker API (`containers`, `events` itd.). Zapobiega bezpośredniemu montowaniu surowego gniazda Dockera przez Mastera. |
| Redis | Cache, kolejki, strumieniowanie logów oraz kanał komunikacji agentów oparty na heartbeat. Działa w prywatnej sieci `dockflare-internal`. |
| DockFlare Agents (opcjonalnie) | Zdalne procesy, które odtwarzają zachowanie Mastera na innych hostach, przesyłają zdarzenia Dockera i zarządzają własnym `cloudflared`. |
| `cloudflared` | Utrzymuje połączenie tunelowe z Cloudflare dla Mastera lub poszczególnych agentów. |

## Warstwowy model konfiguracji

DockFlare używa elastycznego, warstwowego modelu konfiguracji, który łączy automatyzację z precyzyjną kontrolą:

1. **Etykiety Dockera (warstwa bazowa)**: to podstawowa, zautomatyzowana metoda. Cała konfiguracja usługi, czyli hostname, wewnętrzny adres URL oraz polityka dostępu, jest definiowana bezpośrednio w `docker-compose.yml` albo w poleceniu `docker run`. To właśnie ta konfiguracja stanowi źródło prawdy dla usług automatyzowanych.

2. **Grupy dostępu (warstwa abstrakcji)**: aby nie powtarzać złożonych zasad dostępu w wielu usługach, możesz tworzyć wielokrotnego użytku **Grupy dostępu** w panelu administracyjnym. Są to szablony grupujące zestawy reguł, takie jak dostęp dla firmowych adresów e-mail albo z określonych krajów, które synchronizują się z nazwanymi zasadami Cloudflare Access. Przełącznik trybu w oknie dialogowym decyduje, czy DockFlare zastosuje `bypass`, czy `allow`. Następnie całą zasadę można przypisać do kontenera jedną etykietą, na przykład `dockflare.access.group=my-policy-group`.

3. **Nadpisania w panelu administracyjnym (warstwa kontroli)**: panel administracyjny daje najwyższy poziom kontroli. Z panelu możesz:
   * **Nadpisać** politykę dostępu dowolnej usługi, niezależnie od tego, czy została zdefiniowana przez etykiety czy grupę dostępu. Takie nadpisania są trwałe i nie znikają po restarcie kontenera.
   * **Tworzyć ręczne reguły ingress** dla usług, które nie działają w Dockerze, na przykład dla usługi działającej na innej maszynie w sieci.
   * **Przywrócić** konfigurację usługi do stanu wynikającego z etykiet Dockera, odrzucając zmiany wprowadzone z poziomu UI.

Ten model warstwowy pozwala zautomatyzować większość usług za pomocą etykiet Dockera, a jednocześnie zachować możliwość obsługi wyjątków i bardziej złożonych scenariuszy z poziomu panelu administracyjnego.

---

## Architektura zasad dostępu (v3.0.3+)

### System zasad wielokrotnego użytku

DockFlare korzysta teraz z **architektury zasad wielokrotnego użytku**, zgodnej z najlepszymi praktykami Cloudflare:

1. **Grupy dostępu** → synchronizują się z → **Politykami wielokrotnego użytku Cloudflare**
2. **Aplikacje Access** → odwołują się do → **ID polityk wielokrotnego użytku**
3. **Jedno źródło prawdy** → aktualizacja w jednym miejscu obowiązuje wszędzie

Ta architektura eliminuje duplikowanie polityk i pozwala zarządzać nimi zarówno z DockFlare, jak i z panelu Cloudflare, z pełną synchronizacją dwukierunkową.

### Polityki zarządzane przez system

DockFlare automatycznie utrzymuje dwie podstawowe polityki, aby zapewnić spójność:

- **`public-default-bypass`**: polityka bypass dla dostępu publicznego
  - Nieusuwalna polityka systemowa
  - Tworzona automatycznie podczas inicjalizacji
  - Nazwa w Cloudflare: `DockFlare-Default-Public-Access-Bypass`
  - Decyzja: `bypass` z regułą `everyone`
  - Używana przez usługi wymagające publicznego dostępu bez ochrony strefowej
  - Zapobiega powielaniu polityk bypass w panelu Cloudflare

- **`authenticated-default`**: domyślna polityka uwierzytelniania
  - Nieusuwalna polityka systemowa
  - Tworzona automatycznie podczas inicjalizacji
  - Nazwa w Cloudflare: `DockFlare-Default-Authenticated-Access`
  - Decyzja: `allow` z jednorazowym PIN-em i ograniczeniem adresów e-mail
  - Używana w podstawowych scenariuszach dostępu uwierzytelnionego

### Migracja starszych etykiet

DockFlare automatycznie migruje starsze etykiety tak, aby korzystały z polityk systemowych:

- `dockflare.access.policy=bypass` → używa `public-default-bypass`
- `dockflare.access.group=bypass` → używa `public-default-bypass`
- `dockflare.access.policy=authenticate` → używa `authenticated-default`

Migracja odbywa się automatycznie podczas przetwarzania i uzgadniania kontenerów. Nie wymaga ręcznej interwencji.

### Domyślne polityki strefy

Zasady z symbolem wieloznacznym na poziomie strefy (`*.domain.com`) zapewniają warstwowe bezpieczeństwo dzięki priorytetom:

1. **Polityka dla konkretnego hosta** (na przykład `app.example.com`) - najwyższy priorytet
2. **Polityka strefy z symbolem wieloznacznym** (na przykład `*.example.com`) - zabezpieczenie zapasowe
3. **Brak polityki** = dostęp publiczny bez Access App - zachowanie domyślne

Dzięki temu zapomniane lub nieudokumentowane usługi nadal pozostają chronione przez politykę na poziomie strefy.

**Przykład:**
- Polityka strefy: `*.internal.company.com` → wymaga uwierzytelnienia firmowym adresem e-mail
- Konkretny serwis: `public-demo.internal.company.com` → używa `public-default-bypass`
- Zapomniany serwis: `test.internal.company.com` → pozostaje chroniony polityką strefy i wymaga uwierzytelnienia
