# Narzędzia DockFlare CLI

## Oczyść zduplikowane zasady

DockFlare zawiera teraz narzędzie CLI do wykrywania i usuwania zduplikowanych zasad wielokrotnego użytku na koncie Cloudflare.

### Problem

W przypadku uruchomienia wielu instancji DockFlare (lokalnych i wdrożonych) lub wystąpienia dryftu state.json między instancjami, w Cloudflare można utworzyć zduplikowane zasady o tej samej nazwie. To narzędzie konsoliduje je, zachowując najstarsze zasady i usuwając nowsze duplikaty.

### Użycie

#### Podgląd (dry run) — zalecany pierwszy krok

```bash
docker exec dockflare python -m app.cli cleanup-duplicate-policies --dry-run
```

To:
- Zeskanuje wszystkie zasady wielokrotnego użytku na Twoim koncie Cloudflare
- Zidentyfikuje zasady o zduplikowanych nazwach
- Pokaże, które zasady zostaną usunięte (nowsze)
- Pokaże, który identyfikator polityki zostanie zachowany (najstarszy)
- Pokaże aktualizacje `state.json`, które zostaną wprowadzone
- **Nie wprowadzi żadnych zmian**

#### Wykonaj czyszczenie

```bash
docker exec dockflare python -m app.cli cleanup-duplicate-policies --apply
```

To:
- Usunie wszystkie zduplikowane zasady (zachowując najstarsze)
- Zaktualizuje plik `state.json`, aby odwoływał się do poprawnych identyfikatorów zasad
- **Wprowadzi zmiany na Twoim koncie Cloudflare**

### Co robi

1. **Pobiera wszystkie zasady wielokrotnego użytku** z Twojego konta Cloudflare
2. **Grupuje zasady według nazwy** w celu identyfikacji duplikatów
3. **Sortuje według daty utworzenia** – dla każdej nazwy zachowuje najstarszą polisę
4. **Sprawdza aplikacje dostępowe** – identyfikuje, które aplikacje korzystają ze zduplikowanych polityk
5. **Aktualizacje i usunięcia** – dla każdego duplikatu:
   - Aktualizuje aplikacje, których to dotyczy, tak, aby korzystały z zachowanego identyfikatora zasad
   - Następnie usuwa zduplikowaną politykę
6. **Aktualizacja `state.json`** — zapewnia, że wszystkie grupy dostępu odwołują się do prawidłowego (zachowanego) identyfikatora polityki

### Przykładowe wyjście

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

### Funkcje bezpieczeństwa

- **Domyślnie uruchomienie próbne** - Aby wprowadzić zmiany, musisz jawnie użyć `--apply`
- **Zachowuje najstarszą polisę** - Zapewnia, że nie stracisz oryginalnej polisy
- **Ochrona aplikacji dostępu** - Automatycznie aktualizuje aplikacje, aby przed usunięciem korzystały z zachowanych zasad
- **Aktualizacja state.json** - Automatycznie naprawia odniesienia do usuniętych zasad
- **Szczegółowe rejestrowanie** - Pokazuje dokładnie, co zostanie (lub zostało) zrobione

### Kiedy używać

- Po wykryciu zduplikowanych zasad systemowych (DockFlare-Default-*)
- Po uruchomieniu wielu instancji DockFlare, które utworzyły zduplikowane zasady użytkownika
- Przed aktualizacją wersji głównej w celu oczyszczenia konta Cloudflare
- Podczas rozwiązywania problemów związanych z zasadami

### Notatki

- Narzędzie wymaga skonfigurowania DockFlare z prawidłowymi poświadczeniami Cloudflare
- Działa na **wszystkich zasadach wielokrotnego użytku** na Twoim koncie, a nie tylko tych zarządzanych przez DockFlare
- **Automatycznie obsługuje aplikacje Access** - Narzędzie wykrywa aplikacje korzystające z zduplikowanych zasad, aktualizuje je tak, aby korzystały z zachowanych zasad, a następnie bezpiecznie usuwa duplikaty
- **Nakaz bezpiecznego wykonania** - Aplikacje są aktualizowane PRZED usunięciem polityk, co zapobiega przestojom i lukom w kontroli dostępu
- Zawsze uruchamiaj najpierw z `--dry-run`, aby wyświetlić podgląd zmian
- Usunięcie jest trwałe i nie można go cofnąć (z wyjątkiem ręcznego odtworzenia zasad)
