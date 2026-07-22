# Predvolené politiky zóny – wildcard ochrana

## Prehľad

Predvolené politiky zóny sú funkciou z osvedčených bezpečnostných postupov, ktorá pomocou Cloudflare Access wildcard aplikácií (`*.domain.com`) automaticky chráni všetky subdomény DNS zóny.

## Aký problém to rieši

Bez predvolených politík zóny:
- Zabudnuté služby sú verejne vystavené
- Nové subdomény nemajú žiadnu ochranu, kým sa ručne nenakonfigurujú
- Preklepy v konfigurácii hostname obchádzajú kontroly prístupu
- Rozchádzanie dokumentácie vedie k bezpečnostným medzerám

## Ako to funguje

### Priorita politík

Cloudflare vyhodnocuje Access politiky v tomto poradí:

1. **Presná zhoda hostname** (napr. `app.example.com`)
2. **Wildcard zhoda** (napr. `*.example.com`)
3. **Žiadna zhoda** = verejný prístup (žiadna Access aplikácia)

### Implementácia v DockFlare

Sekcia **Predvolené politiky zóny** v DockFlare:
- Vypisuje všetky tvoje Cloudflare DNS zóny
- Zobrazuje stav ochrany vizuálnymi štítkami
- Umožňuje vytvorenie politík `*.zone.com` jedným kliknutím
- Umožní ti vybrať, ktorá prístupová skupina chráni zónu

## Príručka nastavenia

### Krok 1: Prezri si svoje zóny

1. Prejdi na stránku **Prístupové politiky**
2. Zroluj na **Predvolené politiky zóny (*.tld wildcardy)**
3. Prezri si stav ochrany:
   - 🛡️ **Zelené „Chránené“** – zóna má wildcard politiku
   - ⚠️ **Žlté „Nechránené“** – zóna je zraniteľná

### Krok 2: Vytvor politiky zóny

Pre každú nechránenú zónu:

1. Klikni na tlačidlo **Vytvoriť politiku**
2. Okno zobrazí hostname `*.nazov-zony.com`
3. Vyber vhodnú Access politiku:
   - **Verejné zóny** → `public-default-bypass`
   - **Interné zóny** → politika s overením
   - **Zmiešané zóny** → najprísnejšia politika
4. Klikni na **Vytvoriť politiku zóny**

### Krok 3: Over v Cloudflare

1. Otvor Cloudflare Zero Trust dashboard
2. Prejdi na Access → Applications
3. Hľadaj aplikácie s názvom `Zone Default: *.domain.com`
4. Over, či je politika správna

## Bezpečnostné odporúčania

### Produkčné prostredia

✅ **Vždy zapni predvolené politiky zóny**
- Zabraňuje náhodnému vystaveniu
- Zachytáva chyby v konfigurácii
- Chráni pred útokmi na objavovanie subdomén

### Stratégia výberu politiky

- **Domény s verejným obsahom** (blogy, marketing): `public-default-bypass`
- **Domény s internými nástrojmi**: overenie e-mailom/doménou
- **Domény s citlivými dátami**: overenie so zapnutým MFA
- **Vývojové domény**: uzamkni najprísnejšou politikou

### Monitoring

Pravidelne prehodnocuj:
- Ktoré zóny majú ochranu (stránka **Prístupové politiky**)
- Logy Access aplikácií v Cloudflare
- Zoznam aktívnych subdomén oproti nakonfigurovaným politikám

## Riešenie problémov

### Chyba „Policy already exists“

Access aplikácia `*.domain.com` už existuje. Mohla byť:
- Vytvorená ručne v Cloudflare
- Vytvorená DockFlare skôr
- Vytvorená iným nástrojom

**Riešenie:** Spravuj ju priamo v Cloudflare, alebo ju zmaž a znovu vytvor cez DockFlare.

### Služba je stále dostupná bez overenia

Skontroluj prioritu politík:
1. Over, či má služba politiku konkrétneho hostname
2. Potvrď, že wildcard zóny existuje a je správne nakonfigurovaný
3. Ak má byť služba verejná napriek ochrane zóny, pridaj label `dockflare.access.group=public-default-bypass`

### Obídenie ochrany zóny pre verejné služby

Ak máš politiku overenia na úrovni zóny, no potrebuješ, aby konkrétne služby zostali verejné:

1. Pridaj bypass label do kontajnera:
   ```yaml
   labels:
     - "dockflare.access.group=public-default-bypass"
   ```
2. Tým sa vytvorí Access aplikácia s presným hostname a rozhodnutím bypass
3. Politiky s presným hostname prepíšu wildcard politiky
4. Služba sa stane verejne dostupnou, kým zóna zostane chránená
5. Skontroluj Cloudflare Access logy na poradie vyhodnocovania politík
6. Uisti sa, že DNS záznam smeruje na správny tunel

### Zóna sa nezobrazuje v zozname

Možné príčiny:
- DNS zóna nie je v tvojom Cloudflare účte
- API tokenu chýba oprávnenie `Zone:Zone:Read`
- Zóna je pozastavená alebo zmazaná

**Riešenie:** Over, či zóna existuje v Cloudflare dashboarde a či má API token správne oprávnenia.

## Osvedčené postupy

1. **Najprv vytvor politiky zóny** – pred pridaním služieb
2. **Pri interných zónach použi overenie** – nikdy nepoužívaj bypass
3. **Dokumentuj výnimky** – ak zóna nepotrebuje ochranu, zdokumentuj prečo
4. **Pravidelné audity** – mesačná kontrola stavu ochrany zón
5. **Otestuj pred produkciou** – over, že wildcard politika nerozbije existujúce služby
6. **Princíp najmenších oprávnení** – použi najprísnejšiu politiku, ktorá stále umožní legitímny prístup

## Príklady konfigurácií

### Zóna verejného blogu
```
Zóna: blog.example.com
Politika: public-default-bypass
Výsledok: Všetky subdomény verejne dostupné (*.blog.example.com)
```

### Zóna interných nástrojov
```
Zóna: internal.company.com
Politika: Overenie firemným e-mailom
Výsledok: Všetky subdomény vyžadujú e-mail @company.com (*.internal.company.com)
```

### Zmiešaná vývojová zóna
```
Zóna: dev.company.com
Politika: Overenie vývojárskeho tímu
Výsledok: Všetky vývojové služby predvolene chránené (*.dev.company.com)
Konkrétne prepisy: public-demo.dev.company.com → public-default-bypass
```

## Pochopenie priority politík

### Scenár 1: Konkrétna politika prepíše wildcard

**Nastavenie:**
- Politika zóny: `*.example.com` → vyžaduje overenie
- Konkrétna politika: `blog.example.com` → `public-default-bypass`

**Výsledok:**
- `blog.example.com` → verejné (vyhráva konkrétna politika)
- `api.example.com` → vyžaduje overenie (zachytí ho wildcard)
- `forgotten.example.com` → vyžaduje overenie (zachytí ho wildcard)

### Scenár 2: Wildcard ako záchranná sieť

**Nastavenie:**
- Politika zóny: `*.internal.company.com` → vyžaduje e-mail @company.com
- Konkrétna politika: žiadna pre `test-server.internal.company.com`

**Výsledok:**
- `test-server.internal.company.com` → vyžaduje overenie (chráni ho wildcard)
- Aj keď si ju zabudol nakonfigurovať, politika zóny ju chráni

### Scenár 3: Žiadna ochrana

**Nastavenie:**
- Politika zóny: žiadna pre `*.risky-domain.com`
- Konkrétna politika: `app.risky-domain.com` → overenie

**Výsledok:**
- `app.risky-domain.com` → vyžaduje overenie (konkrétna politika)
- `forgotten.risky-domain.com` → ⚠️ **VEREJNÉ** (žiadny wildcard, ktorý by ho zachytil)

## Integrácia s DockFlare labelmi

### Použitie labelu `default_tld`

Label `dockflare.access.policy=default_tld` povie DockFlare, aby použil wildcard politiku zóny:

```yaml
services:
  my-service:
    image: nginx
    labels:
      - "dockflare.enable=true"
      - "dockflare.hostname=new-app.internal.company.com"
      - "dockflare.service=http://my-service:80"
      - "dockflare.access.policy=default_tld"
```

**Správanie:**
- Ak `*.internal.company.com` existuje → zdedí túto politiku
- Ak politika zóny neexistuje → služba je verejná (nevytvorí sa žiadna Access aplikácia)

### Odporúčanie

Namiesto spoliehania sa na label `default_tld`:
1. Vytvor predvolené politiky zóny v UI
2. Nechaj wildcard politiku automaticky chrániť všetky služby
3. Konkrétne politiky vytváraj len pre výnimky

Zabezpečí to lepšiu bezpečnosť už v predvolenom stave.

## Súvisiaca dokumentácia

- [Osvedčené postupy pre prístupové politiky](Access-Policy-Best-Practices.md)
- [Používanie webového rozhrania](Using-the-Web-UI.md)
- [Docker labely](Container-Labels.md)
- [Ako DockFlare funguje](How-DockFlare-Works.md)
- [Bezpečnostná architektúra](Security-Architecture.md)
