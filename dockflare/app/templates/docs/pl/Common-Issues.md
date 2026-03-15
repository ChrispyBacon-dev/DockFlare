# Typowe problemy

Na tej stronie wymieniono niektóre typowe problemy, jakie mogą napotkać użytkownicy, oraz sposoby ich rozwiązania.

---

### Problem: kontener DockFlare nie uruchamia się lub znajduje się w pętli restartu.

**Rozwiązanie:**
1. **Sprawdź logi Dockera:** Pierwszym krokiem jest zawsze sprawdzenie logów kontenera DockFlare. Uruchom następujące polecenie:
    ```bash
    docker logs dockflare
    ```
2. **Poszukaj błędów:** Poszukaj komunikatów o błędach. Typowe przyczyny obejmują:
    * Nieprawidłowy plik `docker-compose.yml` (np. nieprawidłowa składnia, problemy z montażem woluminu).
    * Problemy z samym demonem Dockera.
    * Problemy z łącznością lub uprawnieniami w przypadku usługi `docker-socket-proxy` lub ustawienia `DOCKER_HOST`.

---

### Problem: rekordy DNS nie są tworzone w Cloudflare.

**Rozwiązanie:**
1. **Sprawdź dzienniki DockFlare:** Poszukaj komunikatów o błędach związanych z interfejsem API Cloudflare. Dzienniki często dokładnie informują, dlaczego wywołanie API nie powiodło się.
2. **Sprawdź uprawnienia tokena API:** Jest to najczęstsza przyczyna. Upewnij się, że Twój token API Cloudflare ma wymagane uprawnienia. Potrzebujesz co najmniej:
    * `Zone:DNS:Edit` dla każdej strefy, którą ma zarządzać DockFlare.
    * `Zone:Zone:Read`
3. **Sprawdź konfigurację strefy:**
    * Upewnij się, że **ID strefy** podany podczas konfiguracji jest prawidłowy.
    * Jeśli używasz etykiety `dockflare.zonename`, sprawdź dokładnie, czy nazwa strefy została wpisana poprawnie.

---

### Problem: polityka dostępu (Zero Trust) nie jest stosowana do usługi.

**Rozwiązanie:**
1. **Sprawdź uprawnienia tokena API:** Upewnij się, że token API ma uprawnienie `Account:Access: Apps and Policies:Edit`.
2. **Sprawdź `UI Override`:** W panelu DockFlare sprawdź, czy reguła ma status `UI Override`. Ten status ma pierwszeństwo przed etykietami.
3. **Sprawdź identyfikator grupy dostępu:** Jeśli używasz `dockflare.access.group`, upewnij się, że identyfikator podany na etykiecie **dokładnie** pasuje do identyfikatora utworzonego dla grupy dostępu na stronie „Zasady dostępu”.
4. **Sprawdź pulpit nawigacyjny Cloudflare:** Zaloguj się do Cloudflare Zero Trust. Przejdź do **Access -> Applications**, aby sprawdzić, czy utworzono aplikację Access. Czasami Cloudflare pokaże tam błąd, który nie będzie widoczny w odpowiedzi API.

---

### Problem: podczas próby uzyskania dostępu do mojej usługi pojawia się błąd `ERR_TOO_MANY_REDIRECTS`.

**Rozwiązanie:**
Ten błąd prawie zawsze występuje z powodu błędnej konfiguracji ustawień SSL/TLS pomiędzy usługą Origin a Cloudflare.

1. **Sprawdź tryb Cloudflare SSL/TLS:** W panelu Cloudflare przejdź do ustawień SSL/TLS dla swojej domeny. Upewnij się, że tryb szyfrowania jest ustawiony na **Pełny (ścisły)**.
2. **Unikaj podwójnych przekierowań:** „Elastyczny” tryb SSL w Cloudflare może powodować ten problem, jeśli Twoja aplikacja zaplecza również próbuje przekierować z HTTP na HTTPS. Przeglądarka utknęła w pętli.
3. **Użyj `https` w adresie URL usługi:** Jeśli Twoja usługa backendu obsługuje protokół HTTPS, użyj `https://` w etykiecie `dockflare.service` (np. `dockflare.service=https://my-app:443`). Dzięki temu połączenie `cloudflared` z Twoją usługą jest również szyfrowane.

---

### Problem: usługa oparta na Traefik/Proxmox działa tylko wtedy, gdy włączona jest opcja „Dopasuj SNI do hosta” Cloudflare.

**Rozwiązanie:**
1. Edytuj regułę ręczną w DockFlare i włącz opcję **Dopasuj SNI do hosta**.
2. Zapisz regułę i zweryfikuj trasę w Cloudflare Zero Trust.
3. Jeśli potrzebujesz także DockFlare do przechowywania pól tras po stronie Cloudflare, których DockFlare nie modeluje, przejdź do **Ustawienia → Ustawienia ogólne** i włącz **Zachowaj niezarządzane pola wejściowe Cloudflare**.

---

### Problem: zarządzanego kontenera `cloudflared-agent` nie można uruchomić z powodu błędu „nieaktualna sieć”.

**Rozwiązanie:**
Może się to zdarzyć, jeśli sieć Docker, z której korzystał agent, została usunięta i utworzona na nowo. DockFlare został zaprojektowany tak, aby obsługiwać to automatycznie.

1. **Uruchom ponownie DockFlare:** Prosty restart kontenera DockFlare (`docker compose restart dockflare`) powinien rozwiązać ten problem.
2. **Jak to działa:** Podczas uruchamiania DockFlare sprawdza kondycję swojego zarządzanego agenta. Jeśli wykryje ten konkretny problem, automatycznie usunie uszkodzony kontener agenta i utworzy nowy z poprawną konfiguracją. Był to konkretny błąd naprawiony w wersji `v1.9.5`. Upewnij się, że korzystasz z najnowszej wersji DockFlare.
