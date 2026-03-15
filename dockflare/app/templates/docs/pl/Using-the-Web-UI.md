# Korzystanie z Web UI

Web UI DockFlare to narzędzie do zarządzania, monitorowania i konfigurowania usług. Ułatwia wykonywanie zadań wykraczających poza samą konfigurację etykiet Dockera.

## Pulpit nawigacyjny (strona główna)

Pierwszą stroną, którą zobaczysz po zalogowaniu się, jest panel główny. To jest Twoje centralne centrum przeglądania stanu wszystkich usług zarządzanych.

* **Tabela zarządzanych reguł ingress:** Ta tabela zawiera listę wszystkich reguł ingress, którymi zarządza DockFlare, niezależnie od tego, czy pochodzą z kontenera Docker, czy zostały utworzone ręcznie.
    * **Nazwa hosta:** Publiczna nazwa hosta usługi.
    * **Usługa:** Wewnętrzny docelowy adres URL.
    * **Źródło:** Wskazuje, czy reguła pochodzi z `Docker`, czy została utworzona `Manually` w interfejsie użytkownika.
    * **Stan:** Pokazuje, czy reguła to `active`, `pending_deletion` lub ma `UI Override`.
    * **Dostęp:** Wyświetla zastosowaną plakietkę grupy dostępu i trybu. Podczas synchronizacji zasad wielokrotnego użytku możesz spodziewać się etykiet `Public` lub `Authenticated`, kaskadowych nazw grup i szybkich łączy do pulpitu nawigacyjnego Cloudflare.
    * **Zarządzaj regułą:** Ten przycisk umożliwia edycję dowolnej reguły.
* **Dzienniki w czasie rzeczywistym:** Pod tabelą znajdziesz przeglądarkę logów w czasie rzeczywistym, która przesyła strumieniowo logi z backendu DockFlare, co jest nieocenione przy debugowaniu.

## Zarządzanie regułami

Web UI zapewnia pełną kontrolę nad regułami ingress.

* **Dodaj regułę ręczną:** Umożliwia utworzenie reguł ingress dla usług, które nie działają w Dockerze (np. na innym komputerze w sieci LAN). Formularz pozwala podać hostname, URL usługi oraz opcjonalnie zastosować Access Group.
* **Edytuj dowolną regułę:** Przycisk „Zarządzaj regułą” obok każdej reguły otwiera okno modalne, w którym możesz zmienić konfigurację. W ten sposób możesz też zastosować UI Override do reguły, która pierwotnie powstała na podstawie etykiet Dockera.
* **Powróć do etykiet:** Jeśli reguła z Dockera ma UI Override, pojawi się przycisk „Powróć do etykiet”. Pozwala on odrzucić ręczne zmiany i ponownie sterować regułą za pomocą etykiet Dockera.

## Strona zasad dostępu

Ta strona jest centralnym miejscem zarządzania **Grupami dostępu** wielokrotnego użytku i zabezpieczania stref DNS za pomocą zasad symboli wieloznacznych.

### Zaawansowane zasady dostępu

W sekcji Grupy dostępu możesz:
* **Utwórz** nowe grupy dostępu, korzystając z modułu dwóch zakładek (uwierzytelnione lub publiczne). Banery ze wskazówkami są aktualizowane na każdej karcie, dzięki czemu wiesz, kiedy DockFlare wyemituje decyzję Cloudflare `allow` lub `bypass`.
* **Edytuj** istniejące grupy dostępu. Modal wymusza weryfikację specyficzną dla trybu (e-maile wymagane do uwierzytelnienia) i utrzymuje widoczność ustawień Geo/IP dla obu trybów.
* **Usuń** Grupy dostępu, które nie są już używane (nie można usunąć zasad systemowych takich jak `public-default-bypass`).
* **Synchronizuj z Cloudflare**, aby zaimportować istniejące zasady wielokrotnego użytku DockFlare ze swojego konta.
* Użyj menu akcji obok każdego wpisu, aby otworzyć pasujące zasady bezpośrednio w panelu kontrolnym Cloudflare za pomocą skrótu ikony Cloudflare.

**Uwaga:** Polityka systemowa `public-default-bypass` jest tworzona automatycznie i zarządzana przez DockFlare. Wszystkie usługi korzystające z dostępu „Pomiń” odwołują się do tej jednej zasady, dzięki czemu pulpit nawigacyjny Cloudflare jest czysty.

### Domyślne zasady strefy (wildcard `*.tld`)

Druga sekcja przedstawia **Domyślne zasady strefy** – najlepszą praktykę w zakresie bezpieczeństwa, która chroni wszystkie subdomeny:

* **Stan ochrony:** Plakietki wizualne pokazują, które strefy DNS mają zasady `*.domain.com` z symbolami wieloznacznymi (chronione 🛡️), a które nie (niechronione ⚠️).
* **Utwórz politykę strefy:** Kliknij „Utwórz politykę” w dowolnej niechronionej strefie, aby utworzyć aplikację dostępu z symbolami wieloznacznymi.
* **Wybierz politykę:** Wybierz, która grupa dostępu powinna chronić wszystkie subdomeny strefy (może to być publiczne obejście, uwierzytelnianie lub dowolna polityka niestandardowa).
* **Bezpieczna siatka:** Nawet jeśli zapomnisz dodać politykę do konkretnej usługi, polityka wildcard na poziomie strefy nadal ją obejmie.

**Najlepsza praktyka:** Utwórz domyślne zasady stref dla wszystkich swoich domen. W przypadku domen publicznych użyj domyślnych zasad obejścia. W przypadku domen wewnętrznych/prywatnych użyj zasad uwierzytelniania. Dzięki temu żadna subdomena nie zostanie przypadkowo ujawniona.

Więcej informacji znajdziesz w przewodniku [Sprawdzone praktyki i przykłady zasad dostępu](Access-Policy-Best-Practices.md).

## Strona ustawień

Strona Ustawienia zawiera różne opcje administracyjne i konfiguracyjne:

* **Tunele Cloudflare:** Ta sekcja zawiera listę wszystkich tuneli Cloudflare znalezionych na Twoim koncie, ich status i podłączonych agentów `cloudflared`. Możesz także wyświetlić wszystkie rekordy DNS CNAME wskazujące na dowolny z Twoich tuneli.
* **Kopia zapasowa i przywracanie:** Pobierz pełne archiwum kopii zapasowej DockFlare (`.zip`) zawierające zaszyfrowaną konfigurację, klucze agenta i stan lub prześlij wcześniej wyeksportowane archiwum, aby przywrócić instancję.
* **Bezpieczeństwo:**
    * **Zmień hasło:** zmień hasło do internetowego interfejsu użytkownika.
    * **Wyłącz logowanie hasłem:** W przypadku zaawansowanych zastosowań, w których umieszczasz DockFlare za innym serwerem proxy uwierzytelniania. **⚠️ Ostrzeżenie:** stwarza to ryzyko bezpieczeństwa ze względu na ekspozycję sieci Docker: dowolny kontener w tej samej sieci Docker może ominąć uwierzytelnianie zewnętrzne i uzyskać bezpośredni dostęp do interfejsu API DockFlare. Zdecydowanie zalecamy zamiast tego korzystanie z dostawców OAuth/OIDC, aby zapewnić wygodę pojedynczego logowania bez poświęcania bezpieczeństwa. Zobacz [Dostęp do Web UI](Accessing-the-Web-UI.md), aby zapoznać się ze wszystkimi konsekwencjami dotyczącymi bezpieczeństwa.
* **Poświadczenia Cloudflare:** Umożliwia aktualizację identyfikatora konta Cloudflare i tokenu API po wstępnej konfiguracji.
* **Konfiguracja podstawowa:** Umożliwia zmianę ustawień, takich jak nazwa tunelu i okres karencji reguły.
