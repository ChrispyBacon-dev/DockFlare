# Korzystanie z panelu administracyjnego

Panel administracyjny DockFlare służy do zarządzania usługami, monitorowania ich stanu i zmiany konfiguracji. Pozwala wygodnie wykonać operacje, których nie da się sensownie obsłużyć samymi etykietami Dockera.

## Pulpit nawigacyjny (strona główna)

Po zalogowaniu najpierw zobaczysz główny pulpit. To centralne miejsce do przeglądania stanu wszystkich usług zarządzanych przez DockFlare.

* **Tabela zarządzanych reguł ingress:** Zawiera wszystkie reguły ingress zarządzane przez DockFlare, niezależnie od tego, czy pochodzą z kontenerów Docker, czy zostały dodane ręcznie.
    * **Nazwa hosta:** Publiczna nazwa hosta usługi.
    * **Usługa:** Wewnętrzny docelowy adres URL.
    * **Źródło:** Pokazuje, czy reguła pochodzi z `Docker`, czy została utworzona ręcznie w panelu.
    * **Stan:** Pokazuje, czy reguła jest `active`, `pending_deletion` albo ma status `UI Override`.
    * **Dostęp:** Wyświetla przypisaną grupę dostępu i tryb. Po synchronizacji zasad wielokrotnego użytku zobaczysz także odpowiednie etykiety, nazwę grupy i szybkie łącza do panelu Cloudflare.
    * **Zarządzaj regułą:** Otwiera edycję wybranej reguły.
* **Dzienniki w czasie rzeczywistym:** Pod tabelą znajdziesz podgląd logów DockFlare, przydatny przy diagnozowaniu problemów.

## Zarządzanie regułami

Panel administracyjny daje pełną kontrolę nad regułami ingress.

* **Dodaj regułę ręczną:** Pozwala utworzyć regułę ingress dla usług, które nie działają w Dockerze, na przykład na innym hoście w sieci LAN. W formularzu podajesz nazwę hosta, adres usługi i opcjonalnie grupę dostępu.
* **Edytuj regułę:** Przycisk „Zarządzaj regułą” obok każdej pozycji otwiera okno edycji. W tym miejscu możesz też zastosować `UI Override` do reguły utworzonej na podstawie etykiet Dockera.
* **Powrót do etykiet:** Jeśli reguła z Dockera ma aktywne `UI Override`, pojawi się przycisk „Powróć do etykiet”. Usuwa on ręczne zmiany i ponownie oddaje sterowanie etykietom Dockera.

## Strona zasad dostępu

Ta strona jest centralnym miejscem zarządzania **Grupami dostępu** wielokrotnego użytku i zabezpieczania stref DNS za pomocą zasad symboli wieloznacznych.

### Zaawansowane zasady dostępu

W sekcji Grupy dostępu możesz:
* **Utwórz** nową grupę dostępu, korzystając z dwóch zakładek: uwierzytelnionej i publicznej. Komunikaty w formularzu pomagają zrozumieć, kiedy DockFlare zastosuje `allow`, a kiedy `bypass`.
* **Edytuj** istniejące grupy dostępu. Formularz pilnuje poprawności danych dla wybranego trybu i pokazuje ustawienia Geo/IP dla obu wariantów.
* **Usuń** nieużywane grupy dostępu. Zasad systemowych, takich jak `public-default-bypass`, nie można usunąć.
* **Synchronizuj z Cloudflare**, aby zaimportować istniejące zasady wielokrotnego użytku DockFlare ze swojego konta.
* Użyj menu akcji obok każdego wpisu, aby otworzyć pasujące zasady bezpośrednio w panelu kontrolnym Cloudflare za pomocą skrótu ikony Cloudflare.

**Uwaga:** Polityka systemowa `public-default-bypass` jest tworzona automatycznie i zarządzana przez DockFlare. Wszystkie usługi korzystające z dostępu „Pomiń” odwołują się do tej jednej zasady, dzięki czemu pulpit nawigacyjny Cloudflare jest czysty.

### Domyślne zasady strefy (`*.tld`)

Druga sekcja przedstawia **Domyślne zasady strefy** – najlepszą praktykę w zakresie bezpieczeństwa, która chroni wszystkie subdomeny:

* **Stan ochrony:** Plakietki wizualne pokazują, które strefy DNS mają zasady `*.domain.com` z symbolami wieloznacznymi (chronione 🛡️), a które nie (niechronione ⚠️).
* **Utwórz politykę strefy:** Kliknij „Utwórz politykę” w dowolnej niechronionej strefie, aby utworzyć aplikację dostępu z symbolami wieloznacznymi.
* **Wybierz politykę:** Wybierz, która grupa dostępu powinna chronić wszystkie subdomeny strefy (może to być publiczne obejście, uwierzytelnianie lub dowolna polityka niestandardowa).
* **Siatka bezpieczeństwa:** Nawet jeśli zapomnisz przypisać politykę do konkretnej usługi, obejmie ją polityka strefy z symbolem wieloznacznym.

**Najlepsza praktyka:** Utwórz domyślne zasady stref dla wszystkich swoich domen. W przypadku domen publicznych użyj domyślnych zasad obejścia. W przypadku domen wewnętrznych/prywatnych użyj zasad uwierzytelniania. Dzięki temu żadna subdomena nie zostanie przypadkowo ujawniona.

Więcej informacji znajdziesz w przewodniku [Sprawdzone praktyki i przykłady zasad dostępu](Access-Policy-Best-Practices.md).

## Strona ustawień

Strona Ustawienia zawiera różne opcje administracyjne i konfiguracyjne:

* **Tunele Cloudflare:** Ta sekcja pokazuje wszystkie tunele Cloudflare znalezione na Twoim koncie, ich stan oraz podłączone instancje `cloudflared`. Możesz też sprawdzić rekordy DNS CNAME wskazujące na dany tunel.
* **Kopia zapasowa i przywracanie:** Pobierz pełne archiwum kopii zapasowej DockFlare (`.zip`) zawierające zaszyfrowaną konfigurację, klucze agenta i stan lub prześlij wcześniej wyeksportowane archiwum, aby przywrócić instancję.
* **Bezpieczeństwo:**
    * **Zmień hasło:** zmienia hasło do panelu administracyjnego.
    * **Wyłącz logowanie hasłem:** opcja dla zaawansowanych wdrożeń, w których DockFlare działa za zewnętrznym mechanizmem uwierzytelniania. **⚠️ Ostrzeżenie:** zwiększa to ryzyko po stronie sieci Docker, ponieważ kontener w tej samej sieci może ominąć uwierzytelnianie zewnętrzne i uzyskać bezpośredni dostęp do API DockFlare. Jeśli zależy Ci na SSO, znacznie bezpieczniej jest skorzystać z OAuth/OIDC. Szczegóły znajdziesz w [Dostępie do panelu administracyjnego](Accessing-the-Web-UI.md).
* **Poświadczenia Cloudflare:** Umożliwia aktualizację identyfikatora konta Cloudflare i tokenu API po wstępnej konfiguracji.
* **Konfiguracja podstawowa:** Umożliwia zmianę ustawień, takich jak nazwa tunelu i okres karencji reguły.
