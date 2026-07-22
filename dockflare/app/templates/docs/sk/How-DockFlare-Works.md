# Ako DockFlare funguje

DockFlare pôsobí ako most medzi tvojím Docker prostredím a sieťou Cloudflare a automatizuje proces bezpečného vystavovania služieb do internetu. Nepretržite sleduje tvojho Docker hostiteľa a pomocou Cloudflare API za teba spravuje tunely, DNS záznamy a prístupové politiky.

## Základný pracovný postup

Základný pracovný postup sa dá rozdeliť do niekoľkých kľúčových krokov:

1.  **Sledovanie Docker udalostí**: DockFlare počúva udalosti Docker socketu, ako `start` a `stop` kontajnerov.

2.  **Detekcia labelov**: Keď sa spustí nový kontajner, DockFlare ho preskúma na labely `dockflare.`. Ak má kontajner `dockflare.enable=true`, DockFlare vie, že ho má spravovať.

3.  **Interakcia s Cloudflare API**: Na základe labelov DockFlare komunikuje s Cloudflare API a nakonfiguruje potrebné zdroje:
    *   **Cloudflare Tunnel**: Pridá ingress pravidlo do tvojho určeného Cloudflare tunela. Toto pravidlo nasmeruje verejný hostname na internú sieťovú adresu kontajnera (napr. `http://my-app:8080`).
    *   **Správa DNS**: Vytvorí CNAME DNS záznam v tvojej Cloudflare DNS zóne, ktorý nasmeruje tvoj požadovaný verejný hostname (napr. `my-app.example.com`) na tvoj Cloudflare tunel.
    *   **Prístupové politiky**: Ak si zadal labely riadenia prístupu, DockFlare vytvorí alebo aktualizuje opakovane použiteľnú Cloudflare Access politiku na zabezpečenie tvojej služby Zero Trust pravidlami (napr. vyžadovanie prihlásenia od tvojho poskytovateľa identity alebo vydanie verejného `bypass`).

4.  **Automatické čistenie**: Keď sa spravovaný kontajner zastaví alebo odstráni, DockFlare automaticky spustí čistiaci proces. Odstráni príslušné ingress pravidlo z Cloudflare tunela, a ak hostname nepoužíva žiadna iná služba, zmaže DNS záznam a Access aplikáciu. Zabraňuje to zastaraným záznamom a udržiava tvoju Cloudflare konfiguráciu prehľadnú.


## Komponenty v skratke

| Komponent | Zodpovednosť |
| --- | --- |
| DockFlare Master | Hostuje UI a API, sleduje Docker udalosti a orchestruje Cloudflare tunely, DNS a Access politiky. Beží bez roota a s Dockerom komunikuje len cez socket proxy. |
| Docker Socket Proxy | Sidecar `tecnativa/docker-socket-proxy`, ktorý Masteru vystavuje minimálnu plochu Docker API (`containers`, `events` atď.). Zabraňuje Masteru pripojiť sa priamo na surový Docker socket. |
| Redis | Cachovanie, fronty, streamovanie logov a heartbeat/spätný kanál agentov. Sídli na privátnej sieti `dockflare-internal`. |
| DockFlare agenti (voliteľné) | Vzdialení pracovníci, ktorí zrkadlia správanie Mastera na iných hostiteľoch, streamujú Docker udalosti späť a spravujú vlastný `cloudflared`. |
| cloudflared | Udržiava tunelové spojenie s Cloudflare pre Master alebo každého agenta. |

## Vrstvený model konfigurácie

DockFlare používa flexibilný, vrstvený prístup ku konfigurácii, ktorý ti dáva automatizáciu aj jemnú kontrolu:

1.  **Docker labely (základná vrstva)**: Hlavná, automatizovaná metóda. Celú konfiguráciu služby — hostname, internú URL služby a prístupovú politiku — definuješ priamo vo svojom `docker-compose.yml` alebo príkaze Docker run. Je to „zdroj pravdy“ pre automatizované služby.

2.  **Prístupové skupiny (abstrakčná vrstva)**: Aby si nemusel opakovať zložité prístupové politiky pri mnohých službách, môžeš vo webovom rozhraní vytvárať opakovane použiteľné **prístupové skupiny**. Sú to šablóny, ktoré zoskupujú súbor prístupových pravidiel (napr. „povoliť firemné e-maily“ alebo „povoliť prístup z konkrétnych krajín“) a synchronizujú sa do pomenovaných opakovane použiteľných Cloudflare Access politík. Prepínač Verejné vs. S overením v okne riadi, či DockFlare vydá rozhodnutie `bypass` alebo `allow`. Celú politiku potom môžeš na kontajner uplatniť jediným labelom (`dockflare.access.group=moja-politicka-skupina`), čím výrazne zjednodušíš svoje labely.

3.  **UI prepisy (riadiaca vrstva)**: Webové rozhranie poskytuje najvyššiu úroveň kontroly. Z dashboardu môžeš:
    *   **Prepísať** prístupovú politiku ktorejkoľvek služby, či už bola definovaná labelmi alebo prístupovou skupinou. Tieto prepisy sú trvalé a reštart kontajnera ich nevráti späť.
    *   **Vytvárať manuálne ingress pravidlá** pre služby, ktoré nebežia v Dockeri (napr. službu na inom stroji v tvojej sieti).
    *   **Vrátiť** konfiguráciu služby späť na to, čo je definované v jej Docker labeloch, a zahodiť tak akékoľvek UI prepisy.

Tento vrstvený model ti umožní pri väčšine služieb „nastaviť a zabudnúť“ pomocou Docker labelov, no zároveň mať možnosť riešiť výnimky a zložité scenáre cez webové rozhranie.

---

## Architektúra prístupových politík (v3.0.3+)

### Systém opakovane použiteľných politík

DockFlare teraz používa **architektúru opakovane použiteľných politík**, ktorá je v súlade s osvedčenými postupmi Cloudflare:

1. **Prístupové skupiny** → synchronizujú sa na → **Cloudflare opakovane použiteľné politiky**
2. **Access aplikácie** → odkazujú na → **ID opakovane použiteľných politík**
3. **Jeden zdroj pravdy** – aktualizuj raz, uplatní sa všade

Táto architektúra odstraňuje duplicitu politík a umožňuje ti spravovať politiky buď z DockFlare, alebo z Cloudflare dashboardu s plnou obojsmernou synchronizáciou.

### Systémom spravované politiky

DockFlare kvôli konzistencii automaticky spravuje dve základné politiky:

- **`public-default-bypass`**: Politika verejného prístupu (bypass)
  - Systémová politika, ktorá sa nedá odstrániť
  - Vytvorí sa automaticky počas inicializácie
  - Cloudflare názov: `DockFlare-Default-Public-Access-Bypass`
  - Rozhodnutie: `bypass` s pravidlom include `everyone`
  - Používajú ju všetky služby vyžadujúce verejný prístup s obídením ochrany zóny
  - Zabraňuje duplicitným bypass politikám v tvojom Cloudflare dashboarde

- **`authenticated-default`**: Predvolená politika overenia
  - Systémová politika, ktorá sa nedá odstrániť
  - Vytvorí sa automaticky počas inicializácie
  - Cloudflare názov: `DockFlare-Default-Authenticated-Access`
  - Rozhodnutie: `allow` s jednorazovým PIN + obmedzením e-mailom
  - Používa sa pre základné scenáre prístupu s overením

### Migrácia starších labelov

DockFlare automaticky migruje staršie labely na použitie systémových politík:

- `dockflare.access.policy=bypass` → používa `public-default-bypass`
- `dockflare.access.group=bypass` → používa `public-default-bypass`
- `dockflare.access.policy=authenticate` → používa `authenticated-default`

Migrácia prebieha transparentne počas spracovania kontajnerov a synchronizácie. Netreba žiadny manuálny zásah.

### Predvolené politiky zóny

Wildcard politiky na úrovni zóny (`*.domain.com`) poskytujú vrstvenú bezpečnosť cez prioritu politík:

1. **Politika konkrétneho hostname** (napr. `app.example.com`) – najvyššia priorita
2. **Wildcard politika zóny** (napr. `*.example.com`) – záloha
3. **Žiadna politika** = verejný prístup (žiadna Access aplikácia) – predvolené

Tým sa zabezpečí, že zabudnuté alebo nezdokumentované služby sú stále chránené politikou na úrovni zóny, ktorá pôsobí ako bezpečnostná záchranná sieť.

**Príklad:**
- Politika zóny: `*.internal.company.com` → vyžaduje overenie firemným e-mailom
- Konkrétna služba: `public-demo.internal.company.com` → používa `public-default-bypass`
- Zabudnutá služba: `test.internal.company.com` → chránená politikou zóny (vyžaduje overenie)
