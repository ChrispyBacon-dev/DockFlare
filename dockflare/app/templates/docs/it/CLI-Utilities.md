# Utilità CLI DockFlare

## Pulisci le policy duplicate

DockFlare ora include un'utilità CLI per rilevare e rimuovere policy riutilizzabili duplicate nel tuo account Cloudflare.

### Problema

Quando si eseguono più istanze DockFlare (locali + distribuite) o si riscontra la deriva di state.json tra le istanze, è possibile creare policy duplicate con lo stesso nome in Cloudflare. Questa utilità li consolida mantenendo la politica più vecchia ed eliminando i duplicati più recenti.

### Utilizzo

#### Anteprima (prova) - Primo passaggio consigliato

```bash
docker exec dockflare python -m app.cli cleanup-duplicate-policies --dry-run
```

Ciò:
- Scansiona tutte le policy riutilizzabili nel tuo account Cloudflare
- Identificare le politiche con nomi duplicati
- Mostra quali policy verranno eliminate (quelle più recenti)
- Mostra quale ID policy verrà mantenuto (quello più vecchio)
- Mostra gli aggiornamenti state.json che verrebbero effettuati
- **NON apportare modifiche effettive**

#### Esegui la pulizia

```bash
docker exec dockflare python -m app.cli cleanup-duplicate-policies --apply
```

Ciò:
- Elimina tutte le policy duplicate (mantenendo le più vecchie)
- Aggiorna state.json per fare riferimento agli ID policy corretti
- **Apporta effettivamente modifiche al tuo account Cloudflare**

### Cosa fa

1. **Recupera tutte le policy riutilizzabili** dal tuo account Cloudflare
2. **Raggruppa le policy per nome** per identificare i duplicati
3. **Ordina per data di creazione**: mantiene la policy più vecchia per ciascun nome
4. **Controlla l'accesso alle applicazioni**: identifica quali applicazioni utilizzano criteri duplicati
5. **Aggiornamenti ed eliminazioni** - per ogni duplicato:
   - Aggiorna le applicazioni interessate per utilizzare l'ID criterio mantenuto
   - Quindi elimina la politica duplicata
6. **Aggiornamenti state.json**: garantisce che tutti i gruppi di accesso facciano riferimento all'ID policy corretto (mantenuto).

### Esempio di output

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

### Caratteristiche di sicurezza

- **Esecuzione di prova per impostazione predefinita** - È necessario utilizzare esplicitamente `--apply` per apportare modifiche
- **Mantiene la polizza più vecchia** - Garantisce di non perdere la polizza originale
- **Accesso alla protezione delle applicazioni**: aggiorna automaticamente le applicazioni per utilizzare i criteri mantenuti prima dell'eliminazione
- **Aggiorna state.json**: corregge automaticamente i riferimenti alle policy eliminate
- **Registrazione dettagliata** - Mostra esattamente cosa sarà (o è stato) fatto

### Quando usarlo

- Dopo aver scoperto le policy di sistema duplicate (DockFlare-Default-*)
- Dopo aver eseguito più istanze DockFlare che hanno creato policy utente duplicate
- Prima degli aggiornamenti principali della versione per ripulire il tuo account Cloudflare
- Durante la risoluzione di problemi relativi alle policy

### Note

- L'utilità richiede che DockFlare sia configurato con credenziali Cloudflare valide
- Funziona su **tutte le policy riutilizzabili** nel tuo account, non solo su quelle gestite da DockFlare
- **Gestisce automaticamente le applicazioni di accesso** - L'utilità rileva le app che utilizzano policy duplicate, le aggiorna per utilizzare la policy mantenuta, quindi elimina in modo sicuro i duplicati
- **Ordine di esecuzione sicura**: le applicazioni vengono aggiornate PRIMA che le policy vengano eliminate, prevenendo eventuali tempi di inattività o lacune nel controllo degli accessi
- Esegui sempre prima con `--dry-run` per visualizzare in anteprima le modifiche
- L'eliminazione è permanente e non può essere annullata (tranne ricreando manualmente le policy)