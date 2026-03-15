# DockFlare CLI-Hilfsmittu

## Bereinigung doppelter Richtlinien

DockFlare bringt es CLI-Wärchzüg mit, wo doppelte wiederverwendbari Richtlinie i dim Cloudflare-Konto findet u ufroumt.

### Problem

Wänn mehri DockFlare-Instanze laufe oder d `state.json` zwüsche Instanze usenand louft, chöi in Cloudflare mehri Richtlinie mit em glyche Name entstah. Das Tool bhaltet d ältesti Richtlinie u entfernt d neuere Dublette.

### Bruuch

#### Vorschau (`--dry-run`) - dr empfohlni erscht Schritt

```bash
docker exec dockflare python -m app.cli cleanup-duplicate-policies --dry-run
```

Das macht:
- alli wiederverwendbare Richtlinie dürchsueche
- Dublette finde
- zeige, was glöscht würd
- zeige, weli ID bhalte würd
- d Änderige a dr `state.json` vorab azeige
- **nüt würklech ändere**

#### Bereinigung würklech usfüehre

```bash
docker exec dockflare python -m app.cli cleanup-duplicate-policies --apply
```

Das macht:
- alli Dublette definitiv lösche
- d `state.json` uf d rächte Policy-ID aktualisiere
- **würklechi Änderige im Cloudflare-Konto vornäh**

### Was s Tool genau macht

1. Holt alli wiederverwendbare Richtlinie use
2. Gruppiert si nach Name
3. Bhalt pro Name d ältesti
4. Prüeft, weli Access Apps no uf e Dublette zeige
5. Aktualisiert d Apps uf d bhaltni ID
6. Löscht d Dublette
7. Schrybt d `state.json` mit de korrekte Referänze nach

### Beispielausgabe

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

### Sicherheitsmerkmal

- **Dry-Run als Standard:** Für würklechi Änderige bruuchsch explizit `--apply`.
- **Ältesti wird bhalte:** So verlürsch d Ursprungs-Richtlinie nid.
- **Apps wärde vor em Lösche aktualisiert:** Es git kei tote Referänze.
- **`state.json` wird grad mitkorrigiert**
- **Detaillierts Logging**

### Wänn du s bruuche söttsch

- wänn du doppelti Systemrichtlinie gsehsch
- wänn mehri Instanze gsi sy
- vor grössere Upgrades zum Ufruume

### Hinwys

- Es bruucht gültigi Cloudflare-Aamäldedate i DockFlare.
- S Tool arbeitet über **alli** wiederverwendbare Richtlinie im Account.
- Apps wärde immer vor em Lösche aktualisiert.
- Dr Ufruef passiert im Terminal uf dim Docker-Host.
