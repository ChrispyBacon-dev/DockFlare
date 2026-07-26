# Nastavenie a konfigurácia domény

Keď ti Docker kontajnery bežia s profilom `email`, môžeš v webovom rozhraní DockFlare spustiť automatizovaný proces nastavenia.

## Sprievodca nastavením e-mailu

1.  V ľavom bočnom paneli prejdi na stránku **E-mail**.
2.  Klikni na **Nastaviť e-mailovú doménu**.
3.  Vyber **Cloudflare zónu** (doménu), ktorú chceš nakonfigurovať.
4.  Klikni na **Potvrdiť nastavenie**.

### Čo sa deje počas nastavenia?
DockFlare vykoná cez Cloudflare API viacero automatizovaných krokov:
*   **Zapne Email Routing** na tvojej zóne.
*   **Nakonfiguruje DNS:** Vytvorí MX záznamy, SPF (TXT), DMARC (TXT) a DKIM (CNAME) záznamy podľa požiadaviek Cloudflare Email Routing.
*   **Pripraví úložisko:** Vytvorí vyhradený R2 bucket na dočasné tranzitné bufferovanie.
*   **Nasadí Workers:** Nasadí Inbound Worker (na príjem pošty) a Outbound Worker (na odosielanie pošty).
*   **Inicializuje KV:** Vytvorí Cloudflare KV namespace na sledovanie kvót schránok na edge.

## Overenie stavu DNS

Zmeny DNS sa môžu propagovať istý čas. Na stránke E-mail uvidíš kartu **DNS záznamy**.
*   Klikni na **Overiť DNS** a skontroluj aktuálny stav MX, SPF a DMARC záznamov. (DKIM spravuje automaticky Cloudflare Email Routing a tu sa samostatne neoveruje.)
*   Keď systém správne zaznamená záznamy vo verejnom DNS, zobrazí zelené štítky.

## Aktualizácia / opätovné nasadenie workerov

Ak aktualizuješ verziu DockFlare alebo zmeníš oprávnenia API, možno budeš musieť workerov obnoviť.
*   Klikni na tlačidlo **Znova nasadiť Workers**.
*   Tým sa nahrá najnovšia logika workera a znova zosynchronizujú všetky väzby (R2, KV, webhook secrety) bez ovplyvnenia uložených e-mailových dát.

## Odstránenie domény

Ak chceš prestať hostovať e-mail pre doménu:
*   Klikni na **Odstrániť doménu**.
*   Odstránia sa tým routing pravidlá, Inbound a Outbound Workers, tranzitný R2 bucket a DNS záznamy z Cloudflare.
*   **Poznámka:** Toto *nezmaže* tvoje lokálne e-mailové dáta vo volume `mail_data`. Ak chceš vymazať aj správy a prílohy uložené na serveri, zapni v dialógu odstránenia možnosť **Zahrnúť lokálne dáta**.
