# Používanie webového rozhrania

Webové rozhranie DockFlare je výkonný nástroj na správu, monitorovanie a konfiguráciu tvojich služieb. Poskytuje používateľsky prívetivé prostredie pre úlohy, ktoré presahujú jednoduchú konfiguráciu cez Docker labely.

## Dashboard (hlavná stránka)

Prvá stránka, ktorú po prihlásení uvidíš, je hlavný dashboard. Je to tvoje centrálne miesto na sledovanie stavu všetkých spravovaných služieb.

*   **Tabuľka spravovaných ingress pravidiel:** Táto tabuľka vypisuje každé ingress pravidlo, ktoré DockFlare spravuje, či už pochádza z Docker kontajnera, alebo bolo vytvorené ručne.
    *   **Hostname:** Verejný hostname služby.
    *   **Služba:** Interná cieľová URL.
    *   **Zdroj:** Udáva, či je pravidlo z `Docker`, alebo bolo vytvorené `Manuálne` v UI.
    *   **Stav:** Zobrazuje, či je pravidlo `aktívne`, `čaká na odstránenie`, alebo má `UI prepis`.
    *   **Prístup:** Zobrazuje uplatnenú prístupovú skupinu a štítok režimu. Uvidíš štítky `Verejné` alebo `S overením`, kaskádované názvy skupín a rýchle odkazy do Cloudflare dashboardu, keď sa synchronizujú opakovane použiteľné politiky.
    *   **Spravovať pravidlo:** Toto tlačidlo ti umožní upraviť ktorékoľvek pravidlo.
*   **Logy v reálnom čase:** Pod tabuľkou nájdeš prehliadač logov v reálnom čase, ktorý streamuje logy z backendu DockFlare — je neoceniteľný pri ladení.

## Správa pravidiel

UI ti dáva plnú kontrolu nad tvojimi ingress pravidlami.

*   **Pridať manuálne pravidlo:** Tlačidlo „Pridať manuálne pravidlo“ ti umožní vytvárať ingress pravidlá pre služby, ktoré nebežia v Dockeri (napr. službu na inom stroji v tvojej LAN). Formulár ti umožní zadať hostname, URL služby a voliteľne uplatniť prístupovú skupinu.
*   **Upraviť ktorékoľvek pravidlo:** Tlačidlo „Spravovať pravidlo“ vedľa každého pravidla otvorí okno, kde môžeš zmeniť jeho konfiguráciu. Takto uplatníš UI prepis na pravidlo, ktoré bolo pôvodne vytvorené z Docker labelov.
*   **Vrátiť na labely:** Ak má pravidlo z Dockeru UI prepis, zobrazí sa tlačidlo „Vrátiť na labely“, ktoré ti umožní zahodiť manuálne zmeny a nechať pravidlo znova riadiť jeho Docker labelmi.

## Stránka prístupových politík

Táto stránka je centrálnym miestom na správu tvojich opakovane použiteľných **prístupových skupín** a zabezpečenie DNS zón wildcard politikami.

### Pokročilé prístupové politiky

V sekcii prístupových skupín môžeš:
*   **Vytvárať** nové prístupové skupiny cez okno s dvoma kartami (S overením vs. Verejné). Nápovedné panely sa menia podľa karty, aby si rozumel, kedy DockFlare vydá Cloudflare rozhodnutie `allow` alebo `bypass`.
*   **Upravovať** existujúce prístupové skupiny. Okno vynucuje validáciu podľa režimu (e-maily povinné pri režime s overením) a nastavenia Geo/IP ponecháva viditeľné pre oba režimy.
*   **Odstraňovať** prístupové skupiny, ktoré sa už nepoužívajú (systémové politiky ako `public-default-bypass` sa nedajú odstrániť).
*   **Synchronizovať z Cloudflare** a importovať existujúce opakovane použiteľné politiky DockFlare zo svojho účtu.
*   Použiť menu akcií vedľa každej položky a otvoriť príslušnú politiku priamo v Cloudflare dashboarde cez skratku s ikonou Cloudflare.

**Poznámka:** Systémovú politiku `public-default-bypass` automaticky vytvára a spravuje DockFlare. Všetky služby používajúce prístup „Bypass“ odkazujú na túto jednu politiku, čím udržiavajú tvoj Cloudflare dashboard prehľadný.

### Predvolené politiky zóny (*.tld wildcardy)

Druhá sekcia zobrazuje **predvolené politiky zóny** — funkciu z osvedčených bezpečnostných postupov, ktorá chráni všetky subdomény:

*   **Stav ochrany:** Vizuálne štítky ukazujú, ktoré DNS zóny majú wildcard politiky `*.domena.com` (Chránené 🛡️) a ktoré nie (Nechránené ⚠️).
*   **Vytvoriť politiku zóny:** Klikni na „Vytvoriť politiku“ pri ktorejkoľvek nechránenej zóne a vytvor wildcard Access aplikáciu.
*   **Vyber politiku:** Vyber, ktorá prístupová skupina má chrániť všetky subdomény zóny (môže to byť verejný bypass, overenie alebo ľubovoľná vlastná politika).
*   **Bezpečnostná záchranná sieť:** Aj keď zabudneš pridať politiku ku konkrétnej službe, wildcard politika na úrovni zóny ju zachytí.

**Osvedčený postup:** Vytvor predvolené politiky zóny pre všetky svoje domény. Pre verejné domény použi predvolenú bypass politiku. Pre interné/privátne domény použi politiku s overením. Tým zabezpečíš, že žiadna subdoména nebude náhodne vystavená.

Viac podrobností nájdeš v príručke [Osvedčené postupy pre prístupové politiky a príklady](Access-Policy-Best-Practices.md).

## Stránka nastavení

Stránka Nastavenia obsahuje rôzne administrátorské a konfiguračné možnosti:

*   **Cloudflare tunely:** Táto sekcia vypisuje všetky Cloudflare tunely nájdené na tvojom účte, ich stav a pripojených agentov `cloudflared`. Môžeš si tiež pozrieť všetky CNAME DNS záznamy smerujúce na ktorýkoľvek z tvojich tunelov.
*   **Záloha a obnovenie:** Stiahni si kompletný zálohovací archív DockFlare (`.zip`) so zašifrovanou konfiguráciou, kľúčmi agentov a stavom, alebo nahraj skôr exportovaný archív na obnovenie inštancie.
*   **Zabezpečenie:**
    *   **Zmeniť heslo:** Zmeň si heslo pre webové rozhranie.
    *   **Vypnúť prihlasovanie heslom:** Pre pokročilé prípady, keď umiestniš DockFlare za iné overovacie proxy. **⚠️ Upozornenie:** Vytvára to bezpečnostné riziko kvôli vystaveniu cez Docker sieť — ktorýkoľvek kontajner na tej istej Docker sieti môže obísť externé overovanie a pristúpiť k API DockFlare priamo. Dôrazne odporúčame namiesto toho použiť OAuth/OIDC providerov pre pohodlie single sign-on bez obetovania bezpečnosti. Úplné bezpečnostné dôsledky nájdeš v [Prístup k webovému rozhraniu](Accessing-the-Web-UI.md#vypnutie-prihlasovania-heslom).
*   **Cloudflare prihlasovacie údaje:** Umožní ti aktualizovať Cloudflare Account ID a API token po úvodnom nastavení.
*   **Základná konfigurácia:** Umožní ti zmeniť nastavenia ako názov tunela a ochrannú lehotu pravidiel.
