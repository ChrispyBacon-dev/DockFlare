# Správa schránok a kvót

Karta **Správa schránok** na stránke E-mail je miesto, kde riadiš, kto môže prijímať poštu a koľko úložiska smie využívať.

## Vytváranie schránok

1.  Klikni na **Pridať schránku**.
2.  **Adresa:** Zadaj požadovaný prefix (napr. `info`). Doména sa automaticky doplní.
3.  **Zobrazované meno:** Meno zobrazené príjemcom (napr. `Tím podpory`).
4.  **Kvóta:** Vyber počiatočný limit úložiska.

## Ako funguje systém kvót

DockFlare používa stupňovitý systém kvót, aby serveru nedošlo miesto na disku a zároveň ponúkol používateľom plynulý zážitok.

### Mäkký limit (kvóta)
Keď schránka prekročí nastavenú kvótu:
*   Systém vloží do doručenej pošty používateľa **varovný e-mail** zo systémovej adresy.
*   Používateľ môže naďalej prijímať poštu, kým nedosiahne tvrdý limit.
*   Ukazovateľ kvóty v hlavnom rozhraní sa zmení na **žltý**.

### Tvrdý limit (odmietnutie)
Tvrdý limit sa automaticky vypočíta ako **mäkký limit + 15 % (minimálne 10 MB rezerva)**.
*   **Odmietnutie na edge:** Odmietnutie prebehne na Cloudflare edge. Poštový server odosielateľa dostane SMTP chybu **5.2.2 Mailbox full**.
*   E-mail sa nikdy nedostane do tvojho R2 tranzitného bucketu ani na lokálny server, čím sa šetrí prenos dát.
*   Ukazovateľ kvóty v hlavnom rozhraní sa zmení na **červený**.

## Catch-all schránky

Catch-all schránka prijíma všetky e-maily poslané na tvoju doménu, ktoré nezodpovedajú žiadnej existujúcej konkrétnej schránke.
1.  Klikni na **Nastaviť catch-all**.
2.  Vyber cieľovú schránku.
3.  Klikni na **Povoliť**.

## Automatické odpovede (režim dovolenky)

Pre ktorúkoľvek schránku môžeš nastaviť automatické odpovede:
1.  Klikni na ikonu **automatickej odpovede** (robot) vedľa schránky.
2.  Zadaj svoju správu a predmet.
3.  Nastav **časové rozpätie**, počas ktorého má byť odpoveď aktívna.
4.  **Interval odpovedí:** Nastav, ako často má automat odpovedať rovnakému odosielateľovi (napr. raz za 24 hodín), aby sa predišlo „e-mailovým slučkám“.
