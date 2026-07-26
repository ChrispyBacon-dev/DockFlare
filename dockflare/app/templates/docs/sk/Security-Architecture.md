# Bezpečnostná architektúra a spevnenie DockFlare

Tento dokument vysvetľuje, ako DockFlare zabezpečuje hlavný uzol (Master) aj zaregistrovaných agentov v DockFlare 3.0+. Dopĺňa bezpečnostný audit tým, že katalogizuje ochranné mechanizmy zabudované v DockFlare a načrtáva odporúčané prevádzkové postupy.

## 1. Model dôvery riadiacej roviny

- **Master ako zdroj pravdy** – DockFlare Master drží všetky Cloudflare prihlasovacie údaje a definície politík. Agenti nikdy nespravujú API tokeny; vykonávajú pokyny prijaté cez overený kanál.
- **API kľúče pre každého agenta** – Registrácia si vyžaduje jedinečný API kľúč vydaný Masterom. Kľúče sú uložené v zašifrovanom úložisku `agent_keys.dat` spolu s metadátami (vlastník, časové značky, stav), takže sa dajú kedykoľvek rotovať alebo zneplatniť.
- **Ochrana Master API** – Administrátorské endpointy (webové UI, `/api/v2/*`) si vyžadujú buď platnú reláciu, alebo hlavný API kľúč. Tokeny sú z odpovedí a logov skryté a dajú sa rotovať bez reštartu stacku.

## 2. Zašifrovaná konfigurácia a správa kľúčov

- **Zašifrovaný `dockflare_config.dat`** – Cloudflare prihlasovacie údaje, UI účty, predvolené hodnoty tunela a hlavný kľúč sú uchované v zašifrovanom blobe chránenom kľúčom `dockflare.key`.
- **Zašifrovaný register agentov** – API kľúče agentov a ich audit metadáta sídlia v `agent_keys.dat`, zašifrované rovnakým Fernet kľúčom. Citlivý materiál sa už v `state.json` nenachádza.
- **Automatický reštart pri obnovení** – Keď sa obnoví zálohovací archív, DockFlare zapíše zašifrované artefakty, znovu načíta runtime stav, zapíše príznak reštartu a ukončí sa. Politika reštartu Dockeru okamžite vráti kontajner späť s novou konfiguráciou.
- **Čitateľný `state.json` pre pozorovateľnosť** – `state.json` zostáva v čitateľnej podobe, aby operátori mohli skúmať pravidlá a agentov. Zašifrované súbory zostávajú smerodajné pre tajné údaje.

## 3. Záruky zálohy a obnovenia

- **Obsah archívu** – Každý zálohovací archív (`dockflare_backup_*.zip`) obsahuje `dockflare_config.dat`, `dockflare.key`, `agent_keys.dat`, `state.json` a `manifest.json` s kontrolnými súčtami a metadátami verzie. Na znovupostavenie hlavného uzla nie sú potrebné žiadne ďalšie súbory.
- **Automatizovaný priebeh obnovenia** – Obnovenie cez sprievodcu nastavením alebo stránku Nastavenia zapíše artefakty, znovu načíta runtime cache a vynúti reštart kontajnera, aby sa zašifrovaná konfigurácia uplatnila okamžite.
- **Spätná kompatibilita** – Nahranie samostatného `state.json` je stále podporované na riešenie problémov alebo čiastočné migrácie. DockFlare naimportuje runtime stav, no zachová existujúcu zašifrovanú konfiguráciu, čím sa vyhne náhodnému resetu prihlasovacích údajov.

## 4. Bezpečnosť siete a komunikácie

- **Prenos cez Cloudflare Tunnel** – Agenti nevystavujú žiadne prichádzajúce porty. Všetka prevádzka prechádza cez Cloudflare tunel spravovaný Masterom, čím sa znižuje útočná plocha na vzdialených hostiteľoch.
- **Overené volania agentov** – REST volania agentov obsahujú ich API kľúč a sú viazané na ich zaznamenané ID agenta. Nezhody tokenov alebo zneplatnené kľúče sú odmietnuté.
- **Redis backplane** – DockFlare sa spolieha na Redis pri cachovaní, streamovaní logov a signalizácii medzi vláknami. Odporúčaný compose stack drží Redis na vyhradenej sieti `dockflare-internal`, aby sa k nemu záťaže na `cloudflare-net` nedostali priamo. Externé Redis služby zabezpeč pomocou auth/TLS, ak ich používaš.
- **Beh s najmenšími oprávneniami** – Master aj agenti bežia ako používateľ `dockflare` (UID/GID 65532) a s Dockerom komunikujú výhradne cez priložený socket proxy, čím udržiavajú vystavenú API plochu na minime.

## 5. Overovanie a autorizácia

- **Spevnené UI prihlásenie** – Predletový sprievodca vynúti vytvorenie UI administrátorského účtu. Prihlasovanie heslom sa dá vypnúť, no **dôrazne sa to neodporúča** kvôli bezpečnostným dôsledkom Docker siete (pozri upozornenie nižšie).
- **Správa relácií** – Relácie Flask-Login sú viazané na zašifrovanú konfiguráciu. Obnovenie zálohy alebo rotácia prihlasovacích údajov automaticky zneplatní existujúce relácie.
- **ACL agentov** – Každý záznam agenta sleduje priradenie tunela, časové značky heartbeatov a čakajúce príkazy. Master doručuje príkazy len agentom, ktorí predložia správny token a majú stav zaregistrovaného.

### ⚠️ Dôležité: Bezpečnostné upozornenie k „Vypnúť prihlasovanie heslom“

DockFlare obsahuje nastavenie „Vypnúť prihlasovanie heslom“ určené pre pokročilé nasadenia, kde je samotný DockFlare chránený externou vrstvou overovania (napríklad Cloudflare Access). **Dôrazne neodporúčame používať túto funkciu** pri väčšine nasadení.

**Bezpečnostné riziká pri zapnutí:**
- **Všetky API endpointy sa stanú dostupnými bez overovania**, keď je toto nastavenie zapnuté
- **Vystavenie cez Docker sieť:** Aj keď je DockFlare za Cloudflare Access na verejnom internete, kontajnery na tej istej Docker sieti môžu obísť externé overovanie a pristúpiť k API DockFlare priamo
- **Žiadne vynucovanie overovania:** Aplikácia predpokladá, že bezpečnosť zabezpečuje externé overovanie

**Príklad útočného vektora:**
```
Internet → Cloudflare Access (chránené) → DockFlare ✅
         ↓
Docker sieť → Iný kontajner → DockFlare API (nechránené) ❌
```

**Odporúčaný prístup:**
Namiesto vypnutia overovania heslom použi jednu z týchto bezpečných možností:
1. **Lokálne DockFlare prihlasovacie údaje** – jednoduché overovanie heslom zabudované v DockFlare
2. **Poskytovatelia OAuth/OIDC** – nastav Google, GitHub, Azure AD alebo iných poskytovateľov identity pre jednoduché single sign-on bez obetovania bezpečnosti

Obe možnosti poskytujú riadne overovanie a zachovávajú pohodlie SSO. OAuth ti dá zážitok single sign-on bez bezpečnostných rizík vypnutého overovania.

**Zhrnutie:** Pokiaľ nemáš veľmi špecifickú, dobre premyslenú bezpečnostnú architektúru so sieťovou izoláciou, nechaj prihlasovanie heslom zapnuté a pre pohodlie použi OAuth.

## 6. Audit a prevádzková viditeľnosť

- **Sledovanie metadát** – Kľúče agentov zaznamenávajú `created_at`, `last_used_at`, `bound_agent_id`, stav a udalosti zneplatnenia. `state.json` zrkadlí časové značky posledného videnia agentov pre rýchly prehľad o stave.
- **Streamovanie logov** – Logy v reálnom čase sa streamujú cez Redis pub/sub. Citlivé hodnoty (tokeny, kľúče) sú pred doručením klientovi skryté.
- **Stavové API** – `/api/v2/overview` konsoliduje stav tunela, agentov a konfigurácie pre monitorovacie systémy alebo GitOps workflowy.

## 7. Odporúčania k nasadeniu

| Oblasť | Odporúčanie |
| --- | --- |
| Docker volumes | Uchovávaj `/app/data` (zašifrovaná konfigurácia, kľúče, stav). Ak je zapnuté logovanie do súboru, uchovávaj aj `/app/logs` a zabezpeč, aby boli host mounty zapisovateľné pre UID/GID 65532 alebo tvoje prepísané build argumenty. |
| Redis | Spusti `redis:7-alpine` popri DockFlare na privátnej sieti (`dockflare-internal`) alebo nasmeruj `REDIS_URL` na spevnenú inštanciu (auth/TLS). Vyhni sa verejnému vystaveniu Redisu. Použi `REDIS_DB_INDEX` na izoláciu dát DockFlare od iných kontajnerov zdieľajúcich tú istú Redis inštanciu. |
| Zálohy | Pravidelne sťahuj `.zip` a ukladaj ho spolu s `dockflare.key`. Oba súbory sú potrebné na dešifrovanie konfigurácie pri obnovení. |
| Agenti | Zaobchádzaj s API kľúčmi ako s prihlasovacími údajmi. Nasadzuj ich so socket proxy, aby boli vystavené len potrebné Docker endpointy, a pamätaj, že kontajner beží ako neprivilegovaný používateľ `dockflare` (UID/GID 65532); zosúlaď oprávnenia hostiteľa alebo prestav s odpovedajúcimi `DOCKFLARE_UID/DOCKFLARE_GID`. |
| Reverzné proxy | Umiestni DockFlare za Cloudflare Access alebo iný dôveryhodný IdP. Ak vypneš prihlasovanie heslom, zabezpeč, aby bolo nadradené overovanie vždy vynútené. |
| Monitoring | Nastav upozornenia na neočakávané reštarty, chýbajúce heartbeaty agentov alebo vydávanie nových kľúčov mimo servisných okien. |

## 8. Budúce vylepšenia (roadmap)

- Voliteľná ochrana Fernet kľúča prístupovou frázou v pokojovom stave.
- Automatizovaná rotácia kľúčov agentov s ochrannými lehotami na postupné zavádzanie.
- Granulárne rozsahy príkazov agentov na oddelenie operácií len na čítanie od meniacich operácií.

---

DockFlare sa naďalej vyvíja s ohľadom na bezpečnosť. Sleduj poznámky k vydaniam pre ďalšie vylepšenia spevnenia a prispievaj nápadmi cez issue tracker, ak potrebuješ ďalšie kontroly.
