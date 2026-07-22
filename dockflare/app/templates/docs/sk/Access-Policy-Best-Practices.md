# Osvedčené postupy pre prístupové politiky a príklady

Najvýkonnejšou bezpečnostnou funkciou DockFlare sú **prístupové skupiny**. Poskytujú centralizovaný, opakovane použiteľný a udržiavateľný spôsob, ako zabezpečiť tvoje služby pomocou Cloudflare Zero Trust.

## „Zlaté pravidlo“: Používaj prístupové skupiny

Jediným najdôležitejším osvedčeným postupom je **používať prístupové skupiny pre všetky svoje bežné prístupové politiky**.

Prístupové skupiny sú šablóny politík, ktoré vytvoríš vo webovom rozhraní DockFlare. Namiesto definovania zložitých pravidiel s viacerými labelmi na každom kontajneri vytvoríš politiku raz a uplatníš ju jediným, čistým labelom. DockFlare v3.0.3 teraz synchronizuje každú skupinu do opakovane použiteľnej Cloudflare Access politiky, takže tá istá sada rozhodnutí môže slúžiť viacerým aplikáciám.

---

## Ako vytvárať a používať prístupové skupiny

Vytvorenie prístupovej skupiny je jednoduchý proces, ktorý prebieha celý v UI DockFlare.

### Krok 1: Vytvor prístupovú skupinu

1.  Prejdi na stránku **Prístupové politiky** z hlavnej navigačnej lišty v UI DockFlare.
2.  Klikni na tlačidlo **„Pridať prístupovú skupinu“**.
3.  Daj svojej skupine **jedinečné a výstižné ID**. Toto ID budeš používať vo svojich Docker labeloch. Napríklad: `admin-users`, `home-network`, `geo-block`.
4.  Vyber **režim prístupu** z kariet v hornej časti okna:
    *   **S overením** vyžaduje, aby sa používatelia prihlásili, a vydáva rozhodnutie `allow`.
    *   **Verejné** používa rozhodnutie `bypass`, takže aplikácia zostáva otvorená, no stále rešpektuje geo filtre.
5.  Vyplň polia, ktoré sa zobrazia pre zvolený režim (e-maily pre režim s overením, voliteľný zoznam krajín pre oba).
6.  Ak si v režime s overením, uprav voliteľné nastavenia ako trvanie relácie, viditeľnosť v App Launcheri a automatické presmerovanie na IdP.
7.  Ulož skupinu. DockFlare zapíše definíciu lokálne a zosynchronizuje ju do Cloudflare ako `DockFlare-AccessGroup-<id>`.

### Krok 2: Uplatni prístupovú skupinu

Po vytvorení máš dva spôsoby, ako uplatniť prístupovú skupinu na službu:

#### A) Cez Docker label (odporúčaný spôsob)

Pre ktorýkoľvek nový alebo existujúci kontajner jednoducho pridaj label `dockflare.access.group` s ID skupiny, ktorú si vytvoril.

```yaml
services:
  grafana:
    image: grafana/grafana
    labels:
      - "dockflare.enable=true"
      - "dockflare.hostname=monitoring.example.com"
      - "dockflare.service=http://grafana:3000"
      # Uplatni celú politiku jedným jednoduchým labelom:
      - "dockflare.access.group=admin-users"
```
Viacero skupín môžeš uplatniť aj cez `dockflare.access.groups` s čiarkou oddeleným zoznamom ID:
`dockflare.access.groups=admin-users,home-network`

#### Systémom spravované politiky

DockFlare poskytuje dve zabudované systémové politiky, ktoré sú automaticky dostupné:

- **`public-default-bypass`** – verejný prístup s rozhodnutím bypass (použi pre skutočne verejné služby)
- **`authenticated-default`** – predvolené overenie s jednorazovým PIN + obmedzením e-mailom

Tieto systémové politiky sa nedajú odstrániť a slúžia ako základ pre ochranu zóny a migráciu starších labelov.

#### B) Cez webové rozhranie (pre manuálne pravidlá alebo prepisy)

Prístupovú skupinu môžeš na ktorékoľvek pravidlo uplatniť aj priamo z dashboardu:
1.  Nájdi ingress pravidlo, ktoré chceš upraviť, na hlavnom dashboarde.
2.  Klikni na tlačidlo **„Spravovať pravidlo“**.
3.  V editačnom okne vyber požadovanú prístupovú skupinu (alebo skupiny) z rozbaľovacieho menu „Prístupové skupiny“.
4.  Ulož zmeny.

Toto je ideálne na uplatnenie politík na manuálne vytvorené pravidlá (pre služby mimo Dockeru) alebo na dočasné prepísanie politiky definovanej Docker labelmi.

---

## Príklady politík

Tu je niekoľko bežných konfigurácií politík, ktoré môžeš vytvoriť v rámci prístupovej skupiny.

### Príklad 1: Overenie e-mailom

Toto je najbežnejší prípad použitia: povolenie len konkrétnym používateľom, ktorí sa vedia overiť tvojím nakonfigurovaným identity providerom (napr. Google, GitHub alebo jednorazový PIN poslaný na e-mail).

*   **ID skupiny:** `admin-users`
*   **Režim:** *S overením*
*   **Povolené e-maily:** `user1@example.com`, `user2@example.com`
*   **Trvanie relácie:** `24h`

DockFlare vytvorí opakovane použiteľnú politiku s rozhodnutím `allow` pre uvedené e-maily a záložným pravidlom `deny` pre všetkých ostatných. Uplatni skupinu cez `dockflare.access.group=admin-users`.

### Príklad 2: Povolenie tvojej domácej IP adresy

Táto politika obmedzí prístup na tvoju domácu sieť, čo ti umožní preskočiť prihlasovaciu výzvu, keď si na dôveryhodnej IP, a inde vynútiť overenie.

1.  **Nájdi svoju verejnú IP:** V prehliadači vyhľadaj „what is my ip“. Zobrazí sa tvoja verejná IP adresa (napr. `203.0.113.55`).
2.  **Vytvor prístupovú skupinu:**
    *   **ID skupiny:** `home-network`
    *   **Režim:** *S overením*
    *   **Povolené e-maily:** `you@example.com`
    *   **Bypass IP:** pridaj `203.0.113.55/32` do poľa zoznamu povolených IP

DockFlare vygeneruje politiku, ktorá najprv obíde tvoj IP rozsah a potom vyžaduje overenie od uvedených e-mailov. Všetci ostatní dostanú rozhodnutie deny.

### Príklad 3: Geo-fencing (blokovanie viacerých krajín)

Táto politika udrží tvoju marketingovú stránku verejnou, no obmedzí prevádzku z konkrétnych regiónov.

*   **ID skupiny:** `public-eu`
*   **Režim:** *Verejné*
*   **Blokované krajiny:** `RU`, `CN`, `KP`

Výsledná opakovane použiteľná politika vydá Cloudflare rozhodnutie `bypass` pre všetkých okrem uvedených krajín. Skombinuj ju s inými skupinami, ak potrebuješ navrstviť ďalšie kontroly (`dockflare.access.groups=public-eu,admin-users`).

---

## Predvolené politiky zóny – osvedčený bezpečnostný postup

### Čo sú predvolené politiky zóny?

Predvolené politiky zóny sú wildcard `*.domain.com` Access aplikácie, ktoré chránia VŠETKY subdomény DNS zóny vrátane tých, ktoré si ešte explicitne nenakonfiguroval.

### Prečo ich potrebuješ

**Problém:** Ak zabudneš pridať k službe Access politiku, je predvolene verejne vystavená.

**Riešenie:** Wildcard politika na úrovni zóny pôsobí ako záchranná sieť. Aj keď zabudneš nakonfigurovať `forgotten-service.yourdomain.com`, politika `*.yourdomain.com` ju zachytí.

### Ako ich nastaviť

1. Prejdi na stránku **Prístupové politiky**
2. Zroluj do sekcie **Predvolené politiky zóny (*.tld wildcardy)**
3. Hľadaj zóny so štítkom „Nechránené“ ⚠️
4. Klikni na **Vytvoriť politiku**
5. Vyber vhodnú prístupovú skupinu:
   - **Pre verejné domény:** použi `public-default-bypass`
   - **Pre interné domény:** použi politiku s overením
   - **Pre zmiešané použitie:** použi svoju najprísnejšiu politiku

### Osvedčené postupy

- ✅ **Vždy vytvor politiky zóny** pre produkčné domény
- ✅ **Použi politiky s overením** pre interné/privátne zóny
- ✅ **Verejný bypass použi** len pre skutočne verejné zóny
- ✅ **Pravidelne prehodnocuj** – kontroluj stav ochrany zón mesačne
- ⚠️ **Pamätaj na prioritu** – politiky konkrétneho hostname prepíšu wildcard politiky

### Poradie priority politík

Cloudflare vyhodnocuje Access politiky v tomto poradí:

1. **Presná zhoda hostname** (napr. `app.example.com`) – najvyššia priorita
2. **Wildcard zhoda** (napr. `*.example.com`) – záloha
3. **Žiadna zhoda** = verejný prístup (žiadna Access aplikácia) – predvolené

Znamená to, že môžeš mať prísnu predvolenú politiku zóny a stále vytvárať konkrétne výnimky pre jednotlivé služby.

---

## Správa externých Cloudflare politík

### Pochopenie typov politík

DockFlare zobrazuje na stránke Prístupové politiky tri typy politík, každý s vizuálnym štítkom:

- **🟦 DockFlare** – politiky vytvorené a spravované cez DockFlare (prefix: `DockFlare-`)
- **🟪 Externé** – politiky vytvorené mimo DockFlare (ručne alebo inými nástrojmi)
- **🟧 Systémové** – systémové politiky, ktoré sa nedajú odstrániť (`public-default-bypass`, `authenticated-default`)

### Synchronizácia externých politík

Predvolene DockFlare importuje len politiky s prefixom `DockFlare-`. Udrží to tvoj zoznam politík prehľadný a zameraný na infraštruktúru kontajnerov.

**Na synchronizáciu VŠETKÝCH Cloudflare politík** (vrátane tých vytvorených ručne):

1. Nastav premennú prostredia: `SYNC_ALL_CLOUDFLARE_POLICIES=true`
2. Reštartuj DockFlare
3. Klikni na **„Synchronizovať z Cloudflare“** na stránke Prístupové politiky

Externé politiky sa zobrazia s fialovým štítkom **„Externé“**.

### Prečo importovať externé politiky?

**Výhody:**
- Kompletná viditeľnosť celého tvojho Cloudflare Access nastavenia
- Opakované použitie existujúcich politík bez ich znovuvytvárania
- Centralizovaná správa v jednom rozhraní
- Uplatnenie ktorejkoľvek politiky na ktorúkoľvek službu (spravovanú cez DockFlare alebo nie)

**Nevýhody:**
- Dlhší zoznam politík, ak máš veľa externých politík
- Riziko náhodnej úpravy politík používaných službami mimo DockFlare

### Organizácia tvojich politík

**Tip pre profíkov:** Premenuj externé politiky v Cloudflare tak, aby používali prefix `DockFlare-`

Externé politiky môžeš organizovať ich premenovaním v Cloudflare dashboarde:

1. Otvor politiku v **Cloudflare Zero Trust**
2. Premenuj ju na použitie prefixu `DockFlare-` (napr. `DockFlare-LegacyVPN` alebo `DockFlare-ThirdPartyApp`)
3. Klikni na **„Synchronizovať z Cloudflare“** v DockFlare
4. Politika sa teraz zobrazí ako politika **spravovaná cez DockFlare** (modrý štítok)

Umožní ti to:
- ✅ Zoskupiť všetky politiky viditeľné v DockFlare s konzistentným pomenovaním
- ✅ Filtrovať a triediť politiky podľa typu
- ✅ Odlíšiť „spravované cez DockFlare“ od „len viditeľné v DockFlare“

### Filtrovanie politík

Použi rozbaľovacie menu **Filter** na zobrazenie konkrétnych typov politík:

- **Všetky politiky** – zobrazí všetko (DockFlare, externé, systémové)
- **Spravované cez DockFlare** – zobrazí len politiky s modrým štítkom
- **Externé** – zobrazí len politiky s fialovým štítkom
- **Systémové** – zobrazí len systémové politiky

### Bezpečnostné prvky

**Ochrana externých politík:**

Pri mazaní alebo úprave externých politík DockFlare zobrazí upozornenie:

> ⚠️ UPOZORNENIE: Toto je EXTERNÁ politika, ktorú nevytvoril DockFlare.
>
> Úprava tejto politiky môže ovplyvniť služby mimo DockFlare.
>
> Si si úplne istý?

Zabraňuje to náhodným zmenám politík spravovaných inými nástrojmi alebo manuálnymi konfiguráciami.

### Osvedčené postupy

1. **Predvolené nastavenie (odporúčané):**
   - Ponechaj `SYNC_ALL_CLOUDFLARE_POLICIES=false` (predvolené)
   - Zobrazia sa len politiky spravované cez DockFlare
   - Čistý, zameraný zoznam politík

2. **Pokročilé nastavenie (skúsení používatelia):**
   - Zapni `SYNC_ALL_CLOUDFLARE_POLICIES=true`
   - Zobraz a spravuj VŠETKY politiky na jednom mieste
   - Premenuj externé politiky na prefix `DockFlare-` pre organizáciu

3. **Hybridný prístup:**
   - Ponechaj synchronizáciu predvolene vypnutú
   - Ručne premenuj dôležité externé politiky na `DockFlare-*` v Cloudflare
   - Automaticky sa zobrazia po ďalšej synchronizácii

4. **Konvencia pomenovania politík:**
   ```
   DockFlare-AccessGroup-<id>     # Automaticky generované prístupovými skupinami
   DockFlare-<custom-name>        # Tvoje premenované externé politiky
   <cokolvek-ine>                 # Čisto externé (viditeľné len ak je synchronizácia zapnutá)
   ```
