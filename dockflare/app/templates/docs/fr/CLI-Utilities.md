# Utilitaires CLI DockFlare

## Nettoyer les politiques en double

DockFlare inclut désormais un utilitaire CLI pour détecter et supprimer les politiques réutilisables en double dans votre compte Cloudflare.

### Problème

Lors de l'exécution de plusieurs instances DockFlare (locales + déployées) ou lors d'une dérive state.json entre les instances, des politiques en double portant le même nom peuvent être créées dans Cloudflare. Cet utilitaire les consolide en conservant la politique la plus ancienne et en supprimant les doublons les plus récents.

### Utilisation

#### Aperçu (exécution à sec) – Première étape recommandée

```bash
docker exec dockflare python -m app.cli cleanup-duplicate-policies --dry-run
```

Cela va :
- Scannez toutes les politiques réutilisables de votre compte Cloudflare
- Identifier les politiques avec des noms en double
- Afficher quelles politiques seraient supprimées (les plus récentes)
- Afficher quel identifiant de politique serait conservé (le plus ancien)
- Afficher les mises à jour state.json qui seraient effectuées
- **N'effectuer AUCUNE modification réelle**

#### Exécuter le nettoyage

```bash
docker exec dockflare python -m app.cli cleanup-duplicate-policies --apply
```

Cela va :
- Supprimer toutes les politiques en double (en gardant la plus ancienne)
- Mettez à jour state.json pour référencer les ID de stratégie corrects
- **Apportez réellement des modifications à votre compte Cloudflare**

### Ce qu'il fait

1. **Récupère toutes les politiques réutilisables** de votre compte Cloudflare
2. **Regroupe les stratégies par nom** pour identifier les doublons
3. **Tri par date de création** - conserve la politique la plus ancienne pour chaque nom
4. **Vérifie les applications d'accès** - identifie les applications qui utilisent des politiques en double
5. **Mises à jour et suppressions** - pour chaque doublon :
   - Met à jour les applications concernées pour utiliser l'ID de stratégie conservé
   - Supprime ensuite la politique en double
6. **Mises à jour state.json** - garantit que tous les groupes d'accès font référence à l'ID de stratégie correct (conservé)

### Exemple de sortie

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

### Caractéristiques de sécurité

- **Exécution à sec par défaut** - Vous devez explicitement utiliser `--apply` pour apporter des modifications
- **Conserve la politique la plus ancienne** - Garantit que vous ne perdez pas la politique d'origine
- **Protection des applications d'accès** - Met automatiquement à jour les applications pour utiliser la stratégie conservée avant la suppression
- **Mises à jour state.json** - Corrige automatiquement les références aux politiques supprimées
- **Journalisation détaillée** - Montre exactement ce qui sera (ou a été) fait

### Quand l'utiliser

- Après avoir découvert des politiques système en double (DockFlare-Default-*)
- Après avoir exécuté plusieurs instances DockFlare qui ont créé des politiques utilisateur en double
- Avant les mises à niveau majeures de version pour nettoyer votre compte Cloudflare
- Lors du dépannage de problèmes liés aux règles

### Remarques

- L'utilitaire nécessite que DockFlare soit configuré avec des informations d'identification Cloudflare valides
- Il fonctionne sur **toutes les politiques réutilisables** de votre compte, pas seulement celles gérées par DockFlare
- **Gère automatiquement les applications d'accès** - L'utilitaire détecte les applications utilisant des politiques en double, les met à jour pour utiliser la politique conservée, puis supprime en toute sécurité les doublons.
- **Ordre d'exécution sécurisé** - Les applications sont mises à jour AVANT la suppression des politiques, évitant ainsi tout temps d'arrêt ou toute lacune dans le contrôle d'accès.
- Exécutez toujours avec `--dry-run` en premier pour prévisualiser les modifications
- La suppression est permanente et ne peut être annulée (sauf en recréant manuellement les politiques)