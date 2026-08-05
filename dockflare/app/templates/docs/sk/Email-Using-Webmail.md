# Používanie webmailu (PWA)

DockFlare obsahuje moderného, responzívneho webmailového klienta, ktorý ti umožní spravovať e-maily z akéhokoľvek zariadenia.

## Prístup k webmailu

Do webmailu sa dá prihlásiť dvoma spôsobmi:

1.  **SSO (Single Sign-On):** Ak si admin prihlásený do hlavného rozhrania DockFlare, klikni na **Otvoriť webmail** na stránke E-mail. Automaticky sa overíš a prihlásiš do svojich schránok.
2.  **Priame prihlásenie:** Prejdi na `https://mail.tvojadomena.com`. Ak si v hlavnom rozhraní nastavil pre svoju schránku heslo, môžeš sa prihlásiť priamo pomocou e-mailovej adresy a hesla.

## Inštalácia ako PWA

Webmail DockFlare je **progresívna webová aplikácia (PWA)**. Znamená to, že si ho môžeš nainštalovať na zariadenie a používať ho ako bežnú aplikáciu.

### Na mobile (iOS/Android) (podpora mobilov sa práve vyvíja a je zatiaľ obmedzená)
*   Otvor URL webmailu v mobilnom prehliadači.
*   **iOS:** Ťukni na ikonu „Zdieľať“ a vyber **Pridať na plochu**.
*   **Android:** Ťukni na tri bodky a vyber **Inštalovať aplikáciu** alebo **Pridať na plochu**.

### Na počítači (Chrome/Edge/Brave)
*   Nájdi ikonu „Inštalovať“ v adresnom riadku (zvyčajne malý monitor so šípkou nadol).
*   Klikni na **Inštalovať**.

## Kľúčové funkcie

*   **Vyhľadávanie:** Na hľadanie e-mailov použi vyhľadávací panel. DockFlare používa fulltextové vyhľadávanie (FTS5) a lokálne indexuje predmety, odosielateľov a telá správ.
*   **Push notifikácie:** V nastaveniach webmailu zapni notifikácie a dostávaj upozornenia na nové e-maily v reálnom čase na počítač či mobil.

## Bezpečnosť

*   **EdDSA overovanie:** Webmail používa pre všetky interakcie s API vysoko bezpečné Ed25519 JSON Web Tokeny (JWT) vydané hlavným serverom DockFlare.
*   **Sanitizácia HTML:** Všetky prichádzajúce HTML e-maily sa pred vykreslením sanitizujú (pomocou DOMPurify), aby ťa ochránili pred cross-site scriptingom (XSS) a sledovacími pixelmi.
