# Prístup k webovému rozhraniu

Keď úspešne spustíš DockFlare kontajner, môžeš pristúpiť k webovému rozhraniu, kde spravuješ nastavenia, sleduješ stav svojich tunelov a ručne konfiguruješ ingress pravidlá.

## Predvolená URL

Predvolene je webové rozhranie DockFlare dostupné na porte `5000`. Otvor webový prehliadač a prejdi na túto URL:

```
http://<ip-tvojho-servera>:5000
```

Nahraď `<ip-tvojho-servera>` IP adresou servera, na ktorom DockFlare beží.

## Prvé nastavenie

Pri prvom prístupe k webovému rozhraniu ťa prevedie **predletový sprievodca nastavením** (Pre-Flight Setup Wizard). Tento sprievodca ti pomôže:

1.  Obnoviť z existujúceho zálohovacieho archívu DockFlare (`dockflare_backup_*.zip`). Ak zvolíš túto možnosť, systém naimportuje tvoju zašifrovanú konfiguráciu, stav a kľúče agentov a potom kontajner automaticky reštartuje, aby ich uplatnil.
2.  Vytvoriť administrátorský účet a heslo pre webové rozhranie.
3.  Zadať tvoje Cloudflare Account ID, Zone ID (voliteľné) a API token.
4.  Potvrdiť nastavenia tunela a dokončiť úvodné kroky.

## Prihlásenie

Po úvodnom nastavení sa ti pri každom prístupe k webovému rozhraniu zobrazí prihlasovacia obrazovka. Na prihlásenie použi heslo, ktoré si vytvoril počas nastavenia.

## Vypnutie prihlasovania heslom

DockFlare obsahuje nastavenie „Vypnúť prihlasovanie heslom“ určené pre pokročilé nasadenia, kde je samotný DockFlare chránený externou vrstvou overovania (napríklad Cloudflare Access). **Dôrazne neodporúčame používať túto funkciu** pri väčšine nasadení.

### Prečo toto nastavenie existuje

Ak prevádzkuješ DockFlare za Cloudflare Access alebo iným overovacím proxy, ktorý vynucuje SSO ešte pred aplikáciou, môžeš zabudované prihlasovanie heslom vypnúť, aby si sa vyhol dvojitému overovaniu.

### Bezpečnostné riziká pri zapnutí

- ⚠️ **Všetky API endpointy sa stanú dostupnými bez overovania**, keď je toto nastavenie zapnuté
- ⚠️ **Vystavenie cez Docker sieť:** Aj keď je DockFlare za Cloudflare Access na verejnom internete, kontajnery na tej istej Docker sieti môžu obísť externé overovanie a pristúpiť k API DockFlare priamo
- ⚠️ **Žiadne vynucovanie overovania:** Aplikácia predpokladá, že bezpečnosť zabezpečuje externé overovanie

### Príklad útočného vektora

```
Internet → Cloudflare Access (chránené) → DockFlare ✅
         ↓
Docker sieť → Iný kontajner → DockFlare API (nechránené) ❌
```

Aj keď je DockFlare chránený Cloudflare Access z internetu, ktorýkoľvek kontajner bežiaci na tej istej Docker sieti môže túto ochranu obísť a priamo pristúpiť k API endpointom DockFlare bez overovania.

### Odporúčaný prístup

Namiesto vypnutia overovania heslom použi jednu z týchto bezpečných možností:

1. **Lokálne DockFlare prihlasovacie údaje** – jednoduché overovanie heslom zabudované v DockFlare
2. **Poskytovatelia OAuth/OIDC** – nastav Google, GitHub, Azure AD alebo iných poskytovateľov identity pre jednoduché single sign-on bez obetovania bezpečnosti (pozri [Nastavenie poskytovateľa OAuth](OAuth-Provider-Setup.md))

Obe možnosti poskytujú riadne overovanie a zachovávajú pohodlie SSO. OAuth ti dá zážitok single sign-on bez bezpečnostných rizík vypnutého overovania.

### Zhrnutie

Pokiaľ nemáš veľmi špecifickú, dobre premyslenú bezpečnostnú architektúru so sieťovou izoláciou, nechaj prihlasovanie heslom zapnuté a pre pohodlie použi OAuth.
