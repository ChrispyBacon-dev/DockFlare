# Architektura bezpieczeństwa i utwardzanie DockFlare

Ten dokument wyjaśnia, w jaki sposób DockFlare chroni zarówno węzeł Master, jak i zarejestrowanych agentów w DockFlare 3.0+. Uzupełnia audyt bezpieczeństwa, podsumowując zabezpieczenia wbudowane w DockFlare oraz zalecane praktyki operacyjne.

## 1. Model zaufania płaszczyzny kontrolnej

- **Master jako źródło prawdy** – DockFlare Master przechowuje wszystkie poświadczenia Cloudflare oraz definicje zasad. Agenci nigdy nie zarządzają tokenami API samodzielnie; wykonują wyłącznie instrukcje otrzymane przez uwierzytelniony kanał.
- **Klucze API dla każdego agenta** – Rejestracja wymaga unikalnego klucza API wydanego przez Mastera. Klucze są przechowywane w zaszyfrowanym magazynie `agent_keys.dat` wraz z metadanymi, takimi jak właściciel, znaczniki czasu i status, dzięki czemu można je rotować lub unieważniać w dowolnym momencie.
- **Ochrona API Mastera** – Endpointy administracyjne, w tym panel administracyjny i `/api/v2/*`, wymagają ważnej sesji albo klucza API Mastera. Tokeny są maskowane w odpowiedziach i logach, a ich rotacja nie wymaga restartu stacka.

## 2. Szyfrowana konfiguracja i zarządzanie kluczami

- **Zaszyfrowany `dockflare_config.dat`** – Poświadczenia Cloudflare, konta interfejsu użytkownika, domyślne ustawienia tuneli oraz klucz Mastera są przechowywane w zaszyfrowanym bloku chronionym przez `dockflare.key`.
- **Zaszyfrowany rejestr agentów** – Klucze API agentów i ich metadane audytowe znajdują się w `agent_keys.dat`, zaszyfrowanym tym samym kluczem Fernet. Wrażliwe informacje nie są już zapisywane w `state.json`.
- **Automatyczny restart po przywróceniu** – Po odtworzeniu archiwum kopii zapasowej DockFlare zapisuje zaszyfrowane artefakty, ponownie ładuje stan środowiska wykonawczego, pozostawia znacznik restartu i kończy pracę. Polityka restartu Dockera natychmiast uruchamia kontener z nową konfiguracją.
- **`state.json` w postaci jawnej dla obserwowalności** – `state.json` pozostaje w zwykłym tekście, aby operatorzy mogli łatwo sprawdzać reguły i agentów. Zaszyfrowane pliki pozostają jednak źródłem prawdy dla sekretów.

## 3. Gwarancje tworzenia kopii zapasowych i przywracania

- **Zawartość archiwum** – Każde archiwum kopii zapasowej (`dockflare_backup_*.zip`) zawiera `dockflare_config.dat`, `dockflare.key`, `agent_keys.dat`, `state.json` oraz `manifest.json` z sumami kontrolnymi i metadanymi wersji. Do odtworzenia węzła Master nie są potrzebne żadne dodatkowe pliki.
- **Zautomatyzowany proces przywracania** – Przywracanie z poziomu kreatora konfiguracji lub strony Settings zapisuje artefakty, ponownie ładuje pamięci podręczne środowiska wykonawczego i wymusza restart kontenera, aby zaszyfrowana konfiguracja została zastosowana natychmiast.
- **Zgodność wsteczna** – Wgrywanie samodzielnego pliku `state.json` jest nadal wspierane na potrzeby troubleshootingu lub częściowych migracji. DockFlare importuje stan środowiska wykonawczego, ale zachowuje istniejącą konfigurację szyfrowaną, co zapobiega przypadkowemu resetowaniu poświadczeń.

## 4. Bezpieczeństwo sieci i komunikacji

- **Transport przez Cloudflare Tunnel** – Agenci nie wystawiają żadnych portów przychodzących. Cały ruch przechodzi przez tunel Cloudflare zarządzany przez Mastera, co ogranicza powierzchnię ataku na zdalnych hostach.
- **Uwierzytelnione wywołania agentów** – Wywołania REST agentów zawierają klucz API i są powiązane z zapisanym identyfikatorem agenta. Błędne lub unieważnione tokeny są odrzucane.
- **Backplane Redis** – DockFlare używa Redis do cache, streamingu logów i sygnalizacji między wątkami. Zalecana stacka Compose utrzymuje Redis w dedykowanej sieci `dockflare-internal`, dzięki czemu workloady z `cloudflare-net` nie mają do niego bezpośredniego dostępu. Jeśli korzystasz z zewnętrznego Redis, zabezpiecz go uwierzytelnianiem i TLS.
- **Uruchomienie z minimalnymi uprawnieniami** – Zarówno Master, jak i agenci działają jako użytkownik `dockflare` (UID/GID 65532) i komunikują się z Dockerem wyłącznie przez dołączony socket proxy, co utrzymuje minimalną powierzchnię ekspozycji API.

## 5. Uwierzytelnianie i autoryzacja

- **Wzmocnione logowanie do UI** – Asystent konfiguracji początkowej wymusza utworzenie konta administratora UI. Logowanie hasłem można wyłączyć, ale **jest to zdecydowanie odradzane** ze względu na konsekwencje bezpieczeństwa w sieci Docker.
- **Zarządzanie sesją** – Sesje Flask-Login są powiązane z szyfrowaną konfiguracją. Przywrócenie kopii zapasowej lub rotacja poświadczeń automatycznie unieważnia istniejące sesje.
- **Listy ACL agentów** – Każdy rekord agenta śledzi przypisanie tunelu, znaczniki czasu heartbeat i oczekujące polecenia. Master przekazuje polecenia tylko agentom przedstawiającym poprawny token i prawidłowy status rejestracji.

### ⚠️ Ważne: ostrzeżenie bezpieczeństwa dotyczące „Disable Password Login”

DockFlare zawiera ustawienie **Disable Password Login**, przeznaczone dla zaawansowanych wdrożeń, w których DockFlare jest już chroniony przez zewnętrzną warstwę uwierzytelniania, na przykład Cloudflare Access. **W większości wdrożeń zdecydowanie odradzamy korzystanie z tej opcji**.

**Ryzyka bezpieczeństwa po włączeniu tej opcji:**
- **Wszystkie endpointy API stają się dostępne bez uwierzytelniania**
- **Ekspozycja przez sieć Docker** – Nawet jeśli DockFlare jest chroniony przez Cloudflare Access w publicznym Internecie, kontenery w tej samej sieci Docker mogą ominąć uwierzytelnianie zewnętrzne i uzyskać bezpośredni dostęp do API DockFlare
- **Brak wymuszania uwierzytelnienia po stronie aplikacji** – Aplikacja zakłada, że bezpieczeństwo jest w pełni obsługiwane przez warstwę zewnętrzną

**Przykład wektora ataku:**
```
Internet → Cloudflare Access (Protected) → DockFlare ✅
         ↓
Docker Network → Other Container → DockFlare API (Unprotected) ❌
```

**Zalecane podejście:**
Zamiast wyłączać uwierzytelnianie hasłem, użyj jednej z poniższych bezpiecznych opcji:
1. **Lokalne poświadczenia DockFlare** – Proste uwierzytelnianie hasłem wbudowane w DockFlare
2. **Dostawcy OAuth/OIDC** – Skonfiguruj Google, GitHub, Azure AD lub innych dostawców tożsamości, aby uzyskać wygodę single sign-on bez osłabiania bezpieczeństwa

Obie opcje zapewniają prawidłowe uwierzytelnienie i jednocześnie zachowują wygodę SSO. OAuth daje tę wygodę bez ryzyk wynikających z wyłączenia uwierzytelniania.

**W skrócie:** jeśli nie masz bardzo specyficznej, dobrze rozumianej architektury bezpieczeństwa z rzeczywistą izolacją sieci, pozostaw logowanie hasłem włączone i używaj OAuth dla wygody.

## 6. Audyt i widoczność operacyjna

- **Śledzenie metadanych** – Klucze agentów zapisują `created_at`, `last_used_at`, `bound_agent_id`, status i zdarzenia unieważnienia. `state.json` odzwierciedla również znaczniki czasu ostatniej aktywności agentów, co ułatwia szybkie kontrole stanu.
- **Streaming logów** – Logi w czasie rzeczywistym są przesyłane przez Redis pub/sub. Wrażliwe wartości, takie jak tokeny i klucze, są maskowane zanim trafią do klienta.
- **API statusu** – `/api/v2/overview` zbiera stan tuneli, agentów i konfiguracji dla systemów monitoringu lub workflow GitOps.

## 7. Zalecenia wdrożeniowe

| Obszar | Zalecenie |
| --- | --- |
| Wolumeny Dockera | Utrzymuj `/app/data` dla szyfrowanej konfiguracji, kluczy i stanu. Utrzymuj też `/app/logs`, jeśli włączone jest logowanie do plików, i upewnij się, że montowania hosta są zapisywalne przez UID/GID 65532 lub nadpisane argumenty buildu. |
| Redis | Uruchamiaj `redis:7-alpine` wraz z DockFlare w prywatnej sieci (`dockflare-internal`) albo wskaż `REDIS_URL` na utwardzoną instancję z auth/TLS. Unikaj publicznego wystawiania Redis. Użyj `REDIS_DB_INDEX`, aby odizolować dane DockFlare od innych kontenerów współdzielących tę samą instancję Redis. |
| Kopie zapasowe | Regularnie pobieraj `.zip` i przechowuj go razem z `dockflare.key`. Do odszyfrowania konfiguracji podczas przywracania potrzebne są oba pliki. |
| Agenci | Traktuj klucze API jak poufne poświadczenia. Wdrażaj agentów z socket proxy, tak aby widoczne były tylko wymagane endpointy Dockera, i pamiętaj, że kontener działa jako nieuprzywilejowany użytkownik `dockflare` (UID/GID 65532); dopasuj uprawnienia hosta lub przebuduj obraz z odpowiednim `DOCKFLARE_UID/DOCKFLARE_GID`. |
| Reverse proxy | Umieść DockFlare za Cloudflare Access lub innym zaufanym IdP. Jeśli wyłączysz logowanie hasłem, upewnij się, że uwierzytelnianie upstream jest zawsze wymuszane. |
| Monitoring | Generuj alerty przy nieoczekiwanych restartach, brakujących sygnałach heartbeat agentów lub wystawieniu nowych kluczy poza planowanymi oknami serwisowymi. |

## 8. Przyszłe ulepszenia (roadmapa)

- Opcjonalna ochrona klucza Fernet passphrase w spoczynku.
- Zautomatyzowana rotacja kluczy agentów z okresami przejściowymi dla wdrożeń etapowych.
- Szczegółowe zakresy poleceń agentów, rozdzielające operacje tylko do odczytu od operacji modyfikujących.

---

DockFlare stale rozwija się z myślą o bezpieczeństwie. Śledź release notes, aby być na bieżąco z kolejnymi usprawnieniami, i zgłaszaj pomysły przez issue tracker, jeśli potrzebujesz dodatkowych mechanizmów kontroli.
