# CLI nástroje DockFlare

## Čistenie duplicitných politík

DockFlare teraz obsahuje CLI nástroj na detekciu a odstránenie duplicitných opakovane použiteľných politík v tvojom Cloudflare účte.

### Problém

Pri prevádzke viacerých inštancií DockFlare (lokálna + nasadená) alebo pri rozchádzaní state.json medzi inštanciami sa v Cloudflare môžu vytvoriť duplicitné politiky s rovnakým názvom. Tento nástroj ich konsoliduje tak, že ponechá najstaršiu politiku a zmaže novšie duplikáty.

### Použitie

#### Náhľad (dry run) – odporúčaný prvý krok

```bash
docker exec dockflare python -m app.cli cleanup-duplicate-policies --dry-run
```

Toto:
- Prehľadá všetky opakovane použiteľné politiky v tvojom Cloudflare účte
- Identifikuje politiky s duplicitnými názvami
- Ukáže, ktoré politiky by sa zmazali (novšie)
- Ukáže, ktoré ID politiky by sa ponechalo (najstaršie)
- Ukáže aktualizácie state.json, ktoré by sa vykonali
- **Neurobí ŽIADNE skutočné zmeny**

#### Vykonanie čistenia

```bash
docker exec dockflare python -m app.cli cleanup-duplicate-policies --apply
```

Toto:
- Zmaže všetky duplicitné politiky (ponechá najstaršiu)
- Aktualizuje state.json tak, aby odkazoval na správne ID politík
- **Skutočne vykoná zmeny v tvojom Cloudflare účte**

### Čo to robí

1. **Načíta všetky opakovane použiteľné politiky** z tvojho Cloudflare účtu
2. **Zoskupí politiky podľa názvu** na identifikáciu duplikátov
3. **Zoradí podľa dátumu vytvorenia** – pre každý názov ponechá najstaršiu politiku
4. **Skontroluje Access aplikácie** – identifikuje, ktoré aplikácie používajú duplicitné politiky
5. **Aktualizuje a zmaže** – pri každom duplikáte:
   - Aktualizuje dotknuté aplikácie tak, aby používali ponechané ID politiky
   - Potom zmaže duplicitnú politiku
6. **Aktualizuje state.json** – zabezpečí, že všetky prístupové skupiny odkazujú na správne (ponechané) ID politiky

### Príklad výstupu

```
============================================================
DUPLICATE POLICY CLEANUP UTILITY
============================================================
Mode: DRY RUN (no changes will be made)

Step 1: Fetching all reusable policies from Cloudflare...
Found 15 total policies

Step 2: Grouping policies by name...

Step 3: Identifying duplicates...
✗ Found 2 policy names with duplicates:

  Policy: 'DockFlare-Default-Public-Access-Bypass' (3 instances)
  Policy: 'DockFlare-AccessGroup-idp-blocker' (3 instances)

Total policies to delete: 4

Step 4: Checking Access Applications for policy usage...
Found 12 Access Applications to check

Step 5: Processing duplicates...

Processing: 'DockFlare-Default-Public-Access-Bypass'
  ✓ Keeping: ID=abc123 (created: 2025-01-01T10:00:00Z)
  ✗ Would delete: ID=def456 (created: 2025-01-02T11:00:00Z)
  ✗ Would delete: ID=ghi789 (created: 2025-01-03T12:00:00Z)

Processing: 'DockFlare-AccessGroup-idp-blocker'
  ✓ Keeping: ID=jkl012 (created: 2025-01-01T09:00:00Z)
  ⚠ Found 2 Access Application(s) using duplicate policies:
    - App: 'DockFlare-app1.example.com' (domain: app1.example.com)
      Using policy: mno345
    - App: 'DockFlare-app2.example.com' (domain: app2.example.com)
      Using policy: pqr678
  📝 Updating applications to use kept policy ID jkl012...
    ✓ Updated app 'DockFlare-app1.example.com': mno345 → jkl012
    ✓ Updated app 'DockFlare-app2.example.com': pqr678 → jkl012
  ✗ Would delete: ID=mno345 (created: 2025-01-02T10:00:00Z)
  ✗ Would delete: ID=pqr678 (created: 2025-01-03T11:00:00Z)

Step 6: Updating state.json with correct policy IDs...
DRY RUN: Would update state.json with the following changes:
  Group 'public-default-bypass': def456 → abc123 (policy: DockFlare-Default-Public-Access-Bypass)
  Group 'idp-blocker': mno345 → jkl012 (policy: DockFlare-AccessGroup-idp-blocker)

============================================================
SUMMARY
============================================================
Total policies scanned: 15
Duplicate policy names found: 2
Policies that would be deleted: 4
Policies that would be kept: 2
============================================================
```

### Bezpečnostné prvky

- **Dry run predvolene** – na vykonanie zmien musíš explicitne použiť `--apply`
- **Ponecháva najstaršiu politiku** – zabezpečí, že neprídeš o pôvodnú politiku
- **Ochrana Access aplikácií** – pred zmazaním automaticky aktualizuje aplikácie na použitie ponechanej politiky
- **Aktualizuje state.json** – automaticky opraví odkazy na zmazané politiky
- **Podrobné logovanie** – ukáže presne, čo sa vykoná (alebo vykonalo)

### Kedy použiť

- Po objavení duplicitných systémových politík (DockFlare-Default-*)
- Po prevádzke viacerých inštancií DockFlare, ktoré vytvorili duplicitné používateľské politiky
- Pred väčšími aktualizáciami verzie na vyčistenie tvojho Cloudflare účtu
- Pri riešení problémov súvisiacich s politikami

### Poznámky

- Nástroj vyžaduje, aby bol DockFlare nakonfigurovaný s platnými Cloudflare prihlasovacími údajmi
- Operuje na **všetkých opakovane použiteľných politikách** v tvojom účte, nielen na tých spravovaných cez DockFlare
- **Automaticky spracúva Access aplikácie** – nástroj zistí aplikácie používajúce duplicitné politiky, aktualizuje ich na použitie ponechanej politiky a potom bezpečne zmaže duplikáty
- **Bezpečné poradie vykonania** – aplikácie sa aktualizujú PRED zmazaním politík, čím sa predchádza výpadku alebo medzerám v riadení prístupu
- Vždy najprv spusti s `--dry-run` na náhľad zmien
- Zmazanie je trvalé a nedá sa vrátiť späť (okrem manuálneho opätovného vytvorenia politík)
