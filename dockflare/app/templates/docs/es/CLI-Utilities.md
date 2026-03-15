# Utilidades CLI de DockFlare

## Limpieza de políticas duplicadas

DockFlare ahora incluye una utilidad CLI para detectar y eliminar políticas reutilizables duplicadas en su cuenta de Cloudflare.

### Problema

Cuando se ejecutan varias instancias de DockFlare (locales + implementadas) o se experimenta una variación de state.json entre instancias, se pueden crear políticas duplicadas con el mismo nombre en Cloudflare. Esta utilidad los consolida manteniendo la política más antigua y eliminando los duplicados más nuevos.

### Uso

#### Vista previa (ejecución en seco): primer paso recomendado

```bash
docker exec dockflare python -m app.cli cleanup-duplicate-policies --dry-run
```

Esto:
- Escanea todas las políticas reutilizables en tu cuenta de Cloudflare
- Identificar políticas con nombres duplicados
- Mostrar qué políticas se eliminarían (las más nuevas)
- Mostrar qué ID de política se conservaría (la más antigua)
- Mostrar las actualizaciones de state.json que se realizarían
- **NO hacer cambios reales**

#### Ejecutar limpieza

```bash
docker exec dockflare python -m app.cli cleanup-duplicate-policies --apply
```

Esto:
- Eliminar todas las políticas duplicadas (manteniendo la más antigua)
- Actualice state.json para hacer referencia a los ID de política correctos.
- ** Realice cambios en su cuenta de Cloudflare **

### Qué hace

1. **Obtiene todas las políticas reutilizables** de su cuenta de Cloudflare
2. **Agrupa políticas por nombre** para identificar duplicados
3. **Ordena por fecha de creación**: mantiene la política más antigua para cada nombre
4. **Comprueba las aplicaciones de acceso**: identifica qué aplicaciones utilizan políticas duplicadas.
5. **Actualizaciones y eliminaciones** - para cada duplicado:
   - Actualiza las aplicaciones afectadas para que utilicen el ID de política conservado.
   - Luego elimina la política duplicada.
6. **Actualiza state.json**: garantiza que todos los grupos de acceso hagan referencia al ID de política correcto (conservado)

### Ejemplo de salida

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

### Funciones de seguridad

- **Ejecución en seco de forma predeterminada** - Debe usar explícitamente `--apply` para realizar cambios
- **Mantiene la política más antigua** - Garantiza que no pierda la política original
- **Protección de aplicaciones de acceso**: actualiza automáticamente las aplicaciones para que utilicen la política mantenida antes de eliminarlas.
- **Actualiza state.json** - Corrige automáticamente las referencias a políticas eliminadas
- **Registro detallado** - Muestra exactamente lo que se hará (o se hizo)

### Cuándo utilizar

- Después de descubrir políticas de sistema duplicadas (DockFlare-Default-*)
- Después de ejecutar múltiples instancias de DockFlare que crearon políticas de usuario duplicadas
- Antes de actualizaciones de versiones importantes para limpiar su cuenta de Cloudflare
- Al solucionar problemas relacionados con políticas

### Notas

- La utilidad requiere que DockFlare esté configurado con credenciales válidas de Cloudflare
- Opera con **todas las políticas reutilizables** de tu cuenta, no solo con las administradas por DockFlare
- **Maneja automáticamente las aplicaciones de acceso** - La utilidad detecta aplicaciones que usan políticas duplicadas, las actualiza para usar la política conservada y luego elimina los duplicados de forma segura.
- **Orden de ejecución segura** - Las aplicaciones se actualizan ANTES de que se eliminen las políticas, lo que evita tiempos de inactividad o brechas en el control de acceso.
- Ejecute siempre con `--dry-run` primero para obtener una vista previa de los cambios.
- La eliminación es permanente y no se puede deshacer (excepto recreando políticas manualmente)