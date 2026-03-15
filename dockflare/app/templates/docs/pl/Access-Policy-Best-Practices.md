# Najlepsze praktyki i przykłady zasad dostępu

Najpotężniejszą funkcją zabezpieczeń DockFlare są **Grupy dostępu**. Zapewniają scentralizowany, możliwy do ponownego użycia i łatwy w utrzymaniu sposób zabezpieczania usług za pomocą Cloudflare Zero Trust.

## „Złota zasada”: używaj grup dostępu

Najważniejsza zasada brzmi: **wszystkie typowe reguły dostępu warto zamknąć w grupach dostępu**.

Grupy dostępu to szablony zasad tworzone w panelu administracyjnym DockFlare. Zamiast definiować na każdym kontenerze złożony zestaw etykiet, tworzysz zasadę raz i przypisujesz ją pojedynczą, czytelną etykietą. W DockFlare v3.0.3 każda grupa synchronizuje się z zasadą Cloudflare Access wielokrotnego użytku, więc ten sam zestaw reguł może obsługiwać wiele aplikacji.

---

## Jak tworzyć i używać grup dostępu

Tworzenie grupy dostępu to prosty proces wykonywany w całości w panelu administracyjnym DockFlare.

### Krok 1: Utwórz grupę dostępu

1. Przejdź do strony **Zasady dostępu** z głównego menu w panelu DockFlare.
2. Kliknij przycisk **„Dodaj grupę dostępu”**.
3. Nadaj swojej grupie **unikalny i opisowy identyfikator**. Ten identyfikator będzie używany w etykietach platformy Docker. Na przykład: `admin-users`, `home-network`, `geo-block`.
4. Wybierz **Tryb dostępu** z zakładek u góry modułu:
    * **Uwierzytelnione** wymaga od użytkowników zalogowania się i wydaje decyzję `allow`.
    * **Publiczny** wykorzystuje decyzję `bypass`, dzięki czemu aplikacja pozostaje otwarta, a jednocześnie uwzględnia filtry geograficzne.
5. Wypełnij dane wejściowe, które pojawią się dla wybranego trybu (e-maile dla uwierzytelnionego, opcjonalna lista krajów dla obu).
6. Dostosuj ustawienia opcjonalne, takie jak czas trwania sesji, widoczność App Launcher i automatyczne przekierowanie do dostawcy tożsamości, jeśli jesteś w trybie uwierzytelnionym.
7. Zapisz grupę. DockFlare zapisuje definicję lokalnie i synchronizuje ją z Cloudflare jako `DockFlare-AccessGroup-<id>`.

### Krok 2: Zastosuj grupę dostępu

Po utworzeniu możesz zastosować grupę dostępu do usługi na dwa sposoby:

#### A) Z etykietą Dockera (zalecany sposób)

W przypadku każdego nowego lub istniejącego kontenera wystarczy dodać etykietę `dockflare.access.group` z identyfikatorem utworzonej grupy.

```yaml
services:
  grafana:
    image: grafana/grafana
    labels:
      - "dockflare.enable=true"
      - "dockflare.hostname=monitoring.example.com"
      - "dockflare.service=http://grafana:3000"
      # Apply the entire policy with one simple label:
      - "dockflare.access.group=admin-users"
```
Możesz także zastosować wiele grup, używając `dockflare.access.groups` z listą identyfikatorów rozdzielonych przecinkami:
`dockflare.access.groups=admin-users,home-network`

#### Zasady zarządzane przez system

DockFlare udostępnia dwie wbudowane polityki systemowe, które są automatycznie dostępne:

- **`public-default-bypass`** - Dostęp publiczny z decyzją o ominięciu (wykorzystanie do usług prawdziwie publicznych)
- **`authenticated-default`** - Domyślne uwierzytelnianie za pomocą jednorazowego PIN-u + ograniczenie e-mail

Tych zasad systemowych nie można usunąć i służą one jako podstawa ochrony stref i migracji starszych etykiet.

#### B) Z poziomu panelu administracyjnego (dla reguł ręcznych lub nadpisań)

Możesz także zastosować grupę dostępu do dowolnej reguły bezpośrednio z pulpitu nawigacyjnego:
1. Znajdź regułę ingress, którą chcesz zmodyfikować, na głównym pulpicie.
2. Kliknij przycisk **„Zarządzaj regułą”**.
3. W trybie edycji wybierz żądane grupy dostępu z menu rozwijanego „Grupy dostępu”.
4. Zapisz zmiany.

Jest to idealne rozwiązanie do stosowania zasad do ręcznie utworzonych reguł (dla usług innych niż Docker) lub do tymczasowego zastępowania zasad zdefiniowanych przez etykiety Docker.

---

## Przykłady zasad

Oto kilka typowych konfiguracji zasad, które można utworzyć w ramach grupy dostępu.

### Przykład 1: Uwierzytelnij przez e-mail

Jest to najczęstszy przypadek użycia: zezwalanie tylko określonym użytkownikom, którzy mogą uwierzytelniać się u skonfigurowanego dostawcy tożsamości (np. Google, GitHub lub jednorazowy kod PIN wysyłany na ich adres e-mail).

* **Identyfikator grupy:** `admin-users`
* **Tryb:** *Uwierzytelnione*
* **Dozwolone e-maile:** `user1@example.com`, `user2@example.com`
* **Czas trwania sesji:** `24h`

DockFlare tworzy politykę wielokrotnego użytku z decyzją `allow` dla wymienionych e-maili i regułą zastępczą `deny` dla wszystkich pozostałych. Zastosuj grupę za pomocą `dockflare.access.group=admin-users`.

### Przykład 2: Zezwól na swój domowy adres IP

Ta zasada ogranicza dostęp do sieci domowej, umożliwiając pominięcie monitu o logowanie, gdy korzystasz z zaufanego adresu IP, podczas wymuszania uwierzytelnienia w innym miejscu.

1. **Znajdź swój publiczny adres IP:** W przeglądarce wyszukaj „jaki jest mój adres IP”. Wyświetlony zostanie Twój publiczny adres IP (np. `203.0.113.55`).
2. **Utwórz grupę dostępu:**
    * **Identyfikator grupy:** `home-network`
    * **Tryb:** *Uwierzytelnione*
    * **Dozwolone e-maile:** `you@example.com`
    * **Pomiń adresy IP:** dodaj `203.0.113.55/32` do pola listy dozwolonych adresów IP

DockFlare generuje politykę, która najpierw omija Twój zakres adresów IP, a następnie wymaga uwierzytelnienia wymienionych wiadomości e-mail. Wszyscy pozostali otrzymają decyzję odmowną.

### Przykład 3: Geo-fencing (blokowanie wielu krajów)

Dzięki tej zasadzie Twoja witryna marketingowa jest publiczna, a jednocześnie ogranicza ruch z określonych regionów.

* **Identyfikator grupy:** `public-eu`
* **Tryb:** *Publiczny*
* **Zablokowane kraje:** `RU`, `CN`, `KP`

Wynikająca z tego polityka wielokrotnego użytku wydaje decyzję Cloudflare `bypass` dla wszystkich, z wyjątkiem wymienionych krajów. Połącz ją z innymi grupami, jeśli chcesz nałożyć dodatkowe elementy sterujące (`dockflare.access.groups=public-eu,admin-users`).

---

## Domyślne zasady strefy — najlepsze praktyki dotyczące bezpieczeństwa

### Jakie są domyślne zasady stref?

Domyślne zasady strefy to aplikacje Access z wzorcem `*.domain.com`, które chronią wszystkie subdomeny strefy DNS, także te, które nie zostały jeszcze jawnie skonfigurowane.

### Dlaczego ich potrzebujesz

**Problem:** Jeśli zapomnisz dodać zasadę dostępu do usługi, domyślnie jest ona widoczna publicznie.

**Rozwiązanie:** Polityka wieloznaczna na poziomie strefy działa jak sieć bezpieczeństwa. Nawet jeśli zapomnisz skonfigurować `forgotten-service.yourdomain.com`, zasada `*.yourdomain.com` to wyłapie.

### Jak je skonfigurować

1. Przejdź do strony **Zasady dostępu**
2. Przewiń do sekcji **Domyślne zasady strefy (*.tld Wildcards)**
3. Poszukaj stref oznaczonych plakietką „Niechronione” ⚠️
4. Kliknij **Utwórz politykę**
5. Wybierz odpowiednią grupę dostępu:
   - **Dla domen publicznych:** Użyj `public-default-bypass`
   - **Dla domen wewnętrznych:** Użyj polityki uwierzytelniania
   - **W przypadku zastosowań mieszanych:** Użyj najbardziej restrykcyjnych zasad

### Najlepsze praktyki

- ✅ **Zawsze twórz zasady stref** dla domen produkcyjnych
- ✅ **Użyj zasad uwierzytelniania** dla stref wewnętrznych/prywatnych
- ✅ **Używaj publicznego bypass** (np. `public-default-bypass`) tylko dla stref, które mają być faktycznie publiczne
- ✅ **Przeglądaj regularnie** - co miesiąc sprawdzaj stan ochrony strefy
- ⚠️ **Pamiętaj o priorytecie** - Określone zasady dotyczące nazw hostów zastępują zasady dotyczące symboli wieloznacznych

### Kolejność priorytetów zasad

Cloudflare ocenia zasady dostępu w następującej kolejności:

1. **Dokładne dopasowanie nazwy hosta** (np. `app.example.com`) — najwyższy priorytet
2. **Dopasowanie symboli wieloznacznych** (np. `*.example.com`) – rozwiązanie zastępcze
3. **Brak dopasowania** = Dostęp publiczny (brak aplikacji Access) – ustawienie domyślne

Oznacza to, że możesz mieć restrykcyjną politykę domyślną strefy i nadal tworzyć określone wyjątki dla poszczególnych usług.

---

## Zarządzanie zewnętrznymi zasadami Cloudflare

### Zrozumienie typów zasad

DockFlare wyświetla trzy typy zasad na stronie Zasady dostępu, każdy z plakietką wizualną:

- **🟦 DockFlare** - Polityki tworzone i zarządzane przez DockFlare (prefiks: `DockFlare-`)
- **🟪 Zewnętrzne** - Polityki utworzone poza DockFlare (ręcznie lub innymi narzędziami)
- **🟧 System** - Nieusuwalne zasady systemowe (`public-default-bypass`, `authenticated-default`)

### Synchronizowanie zasad zewnętrznych

Domyślnie DockFlare importuje tylko zasady z przedrostkiem `DockFlare-`. Dzięki temu lista zasad będzie czysta i skupiona na infrastrukturze kontenerowej.

**Aby zsynchronizować WSZYSTKIE zasady Cloudflare** (w tym te utworzone ręcznie):

1. Ustaw zmienną środowiskową: `SYNC_ALL_CLOUDFLARE_POLICIES=true`
2. Uruchom ponownie DockFlare
3. Kliknij **„Synchronizuj z Cloudflare”** na stronie Zasady dostępu

Zasady zewnętrzne będą oznaczone fioletową plakietką **„Zewnętrzne”**.

### Po co importować zasady zewnętrzne?

**Zalety:**
- Pełna widoczność całej konfiguracji Cloudflare Access
- Ponowne wykorzystanie istniejących polityk bez ich odtwarzania
- Scentralizowane zarządzanie w jednym interfejsie
- Zastosuj dowolną politykę do dowolnej usługi (zarządzanej przez DockFlare lub nie)

**Wady:**
- Dłuższa lista polityk, jeśli masz wiele polityk zewnętrznych
- Ryzyko przypadkowej modyfikacji zasad używanych przez usługi inne niż DockFlare

### Organizowanie zasad

**Wskazówka:** Zmień nazwy zasad zewnętrznych w Cloudflare tak, aby używały prefiksu `DockFlare-`

Możesz uporządkować polityki zewnętrzne, zmieniając ich nazwy w panelu Cloudflare:

1. Otwórz polisę w **Cloudflare Zero Trust**
2. Zmień nazwę, aby używać przedrostka `DockFlare-` (np. `DockFlare-LegacyVPN` lub `DockFlare-ThirdPartyApp`)
3. Kliknij **„Synchronizuj z Cloudflare”** w DockFlare
4. Polityka pojawia się teraz jako zasada **zarządzana przez DockFlare** (niebieska plakietka)

Umożliwia to:
- ✅ Grupuj wszystkie zasady widoczne w DockFlare ze spójnym nazewnictwem
- ✅ Filtruj i sortuj polisy według typu
- ✅ Rozróżnij „zarządzane przez DockFlare” od „tylko widoczne w DockFlare”

### Zasady filtrowania

Użyj menu rozwijanego **Filtr**, aby wyświetlić określone typy zasad:

- **Wszystkie zasady** - Pokazuje wszystko (DockFlare, zewnętrzne, systemowe)
- **DockFlare-Managed** - Pokazuje tylko zasady oznaczone niebieską plakietką
- **Zewnętrzne** — pokazuje tylko zasady z fioletową plakietką
- **System** - Pokazuje tylko zasady systemowe

### Funkcje bezpieczeństwa

**Ochrona polityki zewnętrznej:**

Podczas usuwania lub edytowania polityk zewnętrznych DockFlare wyświetla ostrzeżenie:

> ⚠️ OSTRZEŻENIE: jest to polityka ZEWNĘTRZNA, która nie została stworzona przez DockFlare.
>
> Modyfikacja tej polityki może mieć wpływ na usługi poza DockFlare.
>
> Czy na pewno chcesz to zrobić?

Zapobiega to przypadkowym zmianom zasad zarządzanych za pomocą innych narzędzi lub konfiguracji ręcznych.

### Najlepsze praktyki

1. **Konfiguracja domyślna (zalecana):**
   - Zachowaj `SYNC_ALL_CLOUDFLARE_POLICIES=false` (domyślnie)
   - Wyświetlane są tylko zasady zarządzane przez DockFlare
   - Czysta, skupiona lista zasad

2. **Konfiguracja zaawansowana (użytkownicy zaawansowani):**
   - Włącz `SYNC_ALL_CLOUDFLARE_POLICIES=true`
   - Przeglądaj i zarządzaj WSZYSTKIMI politykami w jednym miejscu
   - Zmień nazwę zasad zewnętrznych na przedrostek `DockFlare-` dla organizacji

3. **Podejście hybrydowe:**
   - Domyślnie synchronizacja jest wyłączona
   - Ręcznie zmień nazwę ważnych polityk zewnętrznych na `DockFlare-*` w Cloudflare
   - Pojawią się automatycznie po następnej synchronizacji

4. **Konwencja nazewnictwa zasad:**
   ```
   DockFlare-AccessGroup-<id>     # Auto-generated by access groups
   DockFlare-<custom-name>         # Your renamed external policies
   <anything-else>                 # Pure external (only visible if sync enabled)
   ```
