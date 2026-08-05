# Content Security Policy (CSP)

## Čo je Content Security Policy?

Content Security Policy (CSP) je štandard webovej bezpečnosti, ktorý pomáha predchádzať určitým typom útokov, najmä Cross-Site Scriptingu (XSS) a útokom typu data injection. Funguje tak, že prehliadaču povie, ktoré zdroje obsahu (skripty, štýly, obrázky atď.) sú dôveryhodné a smú sa na webovej stránke načítať.

## CSP v DockFlare

Samotná aplikácia DockFlare má webové rozhranie. Na ochranu tohto rozhrania a zaistenie jeho bezpečnosti uplatňuje DockFlare na svojom vlastnom UI prísnu Content Security Policy.

Ide o dôležitú internú bezpečnostnú funkciu, ktorá má chrániť teba ako administrátora pred potenciálnymi zraniteľnosťami na strane prehliadača pri používaní dashboardu DockFlare.

## Rozsah CSP

Je dôležité pochopiť, že CSP DockFlare sa vzťahuje **iba na samotné webové rozhranie DockFlare**.

**Neovplyvňuje**, neupravuje ani nepridáva žiadne CSP hlavičky k prevádzke, ktorá sa cez tvoj Cloudflare Tunnel presmerúva do tvojich vlastných aplikácií. Ak chceš uplatniť CSP na vlastné aplikácie, musíš to nastaviť priamo v nich (napr. nastavením HTTP hlavičky `Content-Security-Policy` vo svojom webovom serveri alebo kóde aplikácie).

## Konfigurácia

CSP v DockFlare je neoddeliteľnou súčasťou jeho bezpečnostného nastavenia a **nedá sa používateľsky meniť**. Politika je starostlivo navrhnutá tak, aby bola čo najprísnejšia a zároveň umožnila správne fungovanie UI.

Ak sa chceš dozvedieť viac o tom, ako Content Security Policy vo všeobecnosti funguje, výborným zdrojom je [dokumentácia MDN Web Docs o CSP](https://developer.mozilla.org/en-US/docs/Web/HTTP/CSP).
