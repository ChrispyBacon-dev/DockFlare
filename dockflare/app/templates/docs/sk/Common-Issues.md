# Bežné problémy

Táto stránka uvádza niektoré bežné problémy, na ktoré môžu používatelia naraziť, a spôsob ich riešenia.

---

### Problém: DockFlare kontajner sa nespustí alebo je v reštartovacej slučke.

**Riešenie:**
1.  **Skontroluj Docker logy:** Prvým krokom je vždy kontrola logov DockFlare kontajnera. Spusti tento príkaz:
    ```bash
    docker logs dockflare
    ```
2.  **Hľadaj chyby:** Hľadaj akékoľvek chybové správy. Bežné príčiny sú:
    *   Neplatný súbor `docker-compose.yml` (napr. nesprávna syntax, problémy s pripojením volume).
    *   Problémy so samotným Docker daemonom.
    *   Problémy s pripojením alebo oprávneniami pri službe docker-socket-proxy alebo nastavení `DOCKER_HOST`.

---

### Problém: DNS záznamy sa v Cloudflare nevytvárajú.

**Riešenie:**
1.  **Skontroluj DockFlare logy:** Hľadaj chybové správy súvisiace s Cloudflare API. Logy ti často presne povedia, prečo volanie API zlyhalo.
2.  **Over oprávnenia API tokenu:** Toto je najčastejšia príčina. Uisti sa, že tvoj Cloudflare API token má potrebné oprávnenia. Minimálne potrebuješ:
    *   `Zone:DNS:Edit` pre každú zónu, ktorú má DockFlare spravovať.
    *   `Zone:Zone:Read`
3.  **Over konfiguráciu zóny:**
    *   Uisti sa, že **Zone ID**, ktoré si zadal počas nastavenia, je správne.
    *   Ak používaš label `dockflare.zonename`, dvakrát skontroluj, či je názov zóny napísaný správne.

---

### Problém: Prístupová politika (Zero Trust) sa na službu neuplatňuje.

**Riešenie:**
1.  **Skontroluj oprávnenia API tokenu:** Uisti sa, že tvoj API token má oprávnenie `Account:Access: Apps and Policies:Edit`.
2.  **Skontroluj UI prepisy:** V dashboarde DockFlare skontroluj, či má pravidlo stav „UI prepis“. UI prepisy majú prednosť pred labelmi.
3.  **Skontroluj ID prístupovej skupiny:** Ak používaš `dockflare.access.group`, uisti sa, že ID zadané v labeli **presne** zodpovedá ID, ktoré si vytvoril pre prístupovú skupinu na stránke „Prístupové politiky“.
4.  **Skontroluj Cloudflare dashboard:** Prihlás sa do svojho Cloudflare Zero Trust dashboardu. Prejdi na **Access -> Applications** a pozri, či sa Access aplikácia vytvorila. Cloudflare tam niekedy zobrazí chybu, ktorá nie je viditeľná v odpovedi API.

---

### Problém: Pri pokuse o prístup k službe dostávam chybu `ERR_TOO_MANY_REDIRECTS`.

**Riešenie:**
Táto chyba takmer vždy vzniká kvôli nesprávnej konfigurácii SSL/TLS nastavení medzi tvojou origin službou a Cloudflare.

1.  **Skontroluj SSL/TLS režim Cloudflare:** V Cloudflare dashboarde prejdi do SSL/TLS nastavení pre svoju doménu. Uisti sa, že režim šifrovania je nastavený na **Full (Strict)**.
2.  **Vyhni sa dvojitým presmerovaniam:** Režim „Flexible“ SSL v Cloudflare môže spôsobiť tento problém, ak sa aj tvoja backend aplikácia snaží presmerovať z HTTP na HTTPS. Prehliadač uviazne v slučke.
3.  **Použi `https` v URL svojej služby:** Ak tvoja backend služba podporuje HTTPS, použi `https://` v labeli `dockflare.service` (napr. `dockflare.service=https://my-app:443`). Zabezpečí to, že aj spojenie z `cloudflared` do tvojej služby bude šifrované.

---

### Problém: Služba za Traefikom/Proxmoxom funguje len vtedy, keď je zapnutá Cloudflare možnosť „Match SNI to Host“.

**Riešenie:**
1.  Uprav manuálne pravidlo v DockFlare a zapni **Zhodovať SNI s hostom**.
2.  Ulož pravidlo a over trasu v Cloudflare Zero Trust.
3.  Ak potrebuješ, aby DockFlare zachoval polia trasy na strane Cloudflare, ktoré DockFlare nemodeluje, prejdi na **Nastavenia → Všeobecné nastavenia** a zapni **Zachovať nespravované Cloudflare ingress polia**.

---

### Problém: Spravovaný kontajner `cloudflared-agent` sa nespustí s chybou „stale network“.

**Riešenie:**
Toto sa môže stať, ak bola Docker sieť, ktorú agent používal, odstránená a znovu vytvorená. DockFlare je navrhnutý tak, aby to zvládol automaticky.

1.  **Reštartuj DockFlare:** Jednoduchý reštart DockFlare kontajnera (`docker compose restart dockflare`) by to mal vyriešiť.
2.  **Ako to funguje:** DockFlare pri štarte kontroluje stav svojho spravovaného agenta. Ak zistí tento konkrétny problém, automaticky odstráni pokazený kontajner agenta a vytvorí nový so správnou konfiguráciou. Bola to konkrétna chyba opravená vo verzii `v1.9.5`. Uisti sa, že máš nedávnu verziu DockFlare.
