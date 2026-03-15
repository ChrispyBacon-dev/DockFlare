# DockFlare CLI Utilities

## Cleanup Duplicate Policies

DockFlare now includes a CLI utility to detect and remove duplicate reusable policies in your Cloudflare account.

### Problem

When running multiple DockFlare instances (local + deployed) or experiencing state.json drift between instances, duplicate policies with the same name can be created in Cloudflare. This utility consolidates them by keeping the oldest policy and deleting newer duplicates.

### Usage

#### Preview (Dry Run) - Recommended First Step

```bash
docker exec dockflare python -m app.cli cleanup-duplicate-policies --dry-run
```

This will:
- Scan all reusable policies in your Cloudflare account
- Identify policies with duplicate names
- Show which policies would be deleted (newer ones)
- Show which policy ID would be kept (oldest one)
- Show state.json updates that would be made
- **Make NO actual changes**

#### Execute Cleanup

```bash
docker exec dockflare python -m app.cli cleanup-duplicate-policies --apply
```

This will:
- Delete all duplicate policies (keeping the oldest)
- Update state.json to reference the correct policy IDs
- **Actually make changes to your Cloudflare account**

### What It Does

1. **Fetches all reusable policies** from your Cloudflare account
2. **Groups policies by name** to identify duplicates
3. **Sorts by creation date** - keeps the oldest policy for each name
4. **Checks Access Applications** - identifies which applications are using duplicate policies
5. **Updates & Deletes** - for each duplicate:
   - Updates affected applications to use the kept policy ID
   - Then deletes the duplicate policy
6. **Updates state.json** - ensures all access groups reference the correct (kept) policy ID

### Example Output

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

### Safety Features

- **Dry run by default** - You must explicitly use `--apply` to make changes
- **Keeps oldest policy** - Ensures you don't lose the original policy
- **Access Application protection** - Automatically updates applications to use kept policy before deletion
- **Updates state.json** - Automatically fixes references to deleted policies
- **Detailed logging** - Shows exactly what will be (or was) done

### When to Use

- After discovering duplicate system policies (DockFlare-Default-*)
- After running multiple DockFlare instances that created duplicate user policies
- Before major version upgrades to clean up your Cloudflare account
- When troubleshooting policy-related issues

### Notes

- The utility requires DockFlare to be configured with valid Cloudflare credentials
- It operates on **all reusable policies** in your account, not just DockFlare-managed ones
- **Automatically handles Access Applications** - The utility detects apps using duplicate policies, updates them to use the kept policy, then safely deletes duplicates
- **Safe execution order** - Applications are updated BEFORE policies are deleted, preventing any downtime or access control gaps
- Always run with `--dry-run` first to preview changes
- Deletion is permanent and cannot be undone (except by recreating policies manually)
