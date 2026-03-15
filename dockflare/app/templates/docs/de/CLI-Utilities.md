# DockFlare CLI-Dienstprogramme

## Bereinigung doppelter Richtlinien

DockFlare enthält nun ein CLI-Dienstprogramm, um doppelte wiederverwendbare Richtlinien in Ihrem Cloudflare-Konto zu erkennen und zu entfernen.

### Problem

Wenn Sie mehrere DockFlare-Instanzen ausführen (lokal + bereitgestellt) oder eine Abweichung der `state.json` zwischen Instanzen auftritt, können in Cloudflare doppelte Richtlinien mit demselben Namen entstehen. Dieses Dienstprogramm konsolidiert sie, indem es die älteste Richtlinie beibehält und neuere Duplikate entfernt.

### Verwendung

#### Vorschau (Trockenlauf / Dry Run) - Empfohlener erster Schritt

```bash
docker exec dockflare python -m app.cli cleanup-duplicate-policies --dry-run
```

Dies wird:
- Alle wiederverwendbaren Richtlinien in Ihrem Cloudflare-Konto durchsuchen
- Richtlinien mit doppelten Namen identifizieren
- Zeigen, welche Richtlinien gelöscht würden (die neueren)
- Zeigen, welche Richtlinien-ID beibehalten würde (die älteste)
- Die Änderungen an der `state.json` vorab aufzeigen
- **KEINE tatsächlichen Änderungen vornehmen**

#### Bereinigung ausführen

```bash
docker exec dockflare python -m app.cli cleanup-duplicate-policies --apply
```

Dies wird:
- Alle doppelten Richtlinien dauerhaft löschen (die älteste bleibt bestehen)
- Die `state.json` anhand der verbleibenden korrekten IDs aktualisieren
- **Tatsächliche, destruktive Änderungen an Ihrem Cloudflare-Konto vornehmen**

### Was es macht

1. **Holt alle wiederverwendbaren Richtlinien** aus Ihrem Cloudflare-Konto.
2. **Gruppiert Richtlinien nach Namen**, um Duplikate zu identifizieren.
3. **Sortiert nach Erstellungsdatum** - behält die älteste Richtlinie für jeden Namen.
4. **Überprüft Access Applications** - stellt fest, welche Apps die Duplikate verwenden.
5. **Aktualisiert & Löscht** - Für jedes Duplikat:
   - Betroffene Anwendungen werden aktualisiert, damit sie auf die beibehaltene ID verweisen.
   - Die doppelte Richtlinie wird infolge gelöscht.
6. **Aktualisiert die `state.json`** - um sicherzustellen, dass alle Referenzen lokal stimmen.

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

### Sicherheitsmerkmale

- **Dry-Run als Standard** - Sie müssen explizit `--apply` verwenden, um Änderungen vorzunehmen.
- **Älteste behalten** - Verhindert den Verlust Ihrer Original-Richtlinie.
- **Schutz der Application** - Aktualisiert Ihre Apps vor dem Löschen der doppelten Policy-Referenz.
- **Automatisiert die `state.json`** - Korrigiert tote Referenzen lokal ohne manuelles Eingreifen.
- **Detailliertes Logging** - Transparenz darüber, was im Einzelnen geschieht.

### Wann dies verwendet werden sollte

- Nach Entdeckung doppelter Systemrichtlinien (DockFlare-Default-*).
- Nach Betrieb in diversen Docker Instanzen / Node Umgebungen.
- Vor größeren Versions-Upgrades zum Bereinigen restlicher Policies in Cloudflare.

### Hinweise

- Setzt gültige Cloudflare Anmeldeinformationen in DockFlare voraus.
- Operiert über **alle** wiederverwendbaren Richtlinien im Account (nicht nur DockFlare-eigene).
- **Strikte Operationsreihenfolge** - Access Applications werden aktualisiert, bevor Policies gelöscht werden.
- Der Aufruf erfolgt im Terminal auf Ihrer Docker-Host-Umgebung.
