# DockFlare CLI 实用程序

## 清理重复策略

DockFlare 现在包含一个 CLI 实用程序，用于检测和删除 Cloudflare 帐户中重复的可重用策略。

### 问题

当运行多个 DockFlare 实例（本地 + 部署）或实例之间出现 state.json 漂移时，可能会在 Cloudflare 中创建同名的重复策略。该实用程序通过保留最旧的策略并删除较新的重复项来整合它们。

### 用法

#### 预览（试运行）- 推荐的第一步

```bash
docker exec dockflare python -m app.cli cleanup-duplicate-policies --dry-run
```

这将：
- 扫描您的 Cloudflare 帐户中的所有可重复使用的策略
- 识别具有重复名称的策略
- 显示哪些策略将被删除（较新的策略）
- 显示将保留哪个策略 ID（最旧的一个）
- 显示将进行的 state.json 更新
- **不进行任何实际更改**

#### 执行清理

```bash
docker exec dockflare python -m app.cli cleanup-duplicate-policies --apply
```

这将：
- 删除所有重复的策略（保留最旧的）
- 更新 state.json 以引用正确的策略 ID
- **实际对您的 Cloudflare 帐户进行更改**

### 它的作用

1. **从您的 Cloudflare 帐户获取所有可重复使用的策略**
2. **按名称对策略进行分组**以识别重复项
3. **按创建日期排序** - 保留每个名称最旧的策略
4. **检查访问应用程序** - 识别哪些应用程序正在使用重复的策略
5. **更新和删除** - 对于每个重复项：
   - 更新受影响的应用程序以使用保留的策略 ID
   - 然后删除重复的策略
6. **更新 state.json** - 确保所有访问组引用正确的（保留的）策略 ID

### 输出示例

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

### 安全特性

- **默认情况下试运行** - 您必须显式使用 `--apply` 进行更改
- **保留最旧的策略** - 确保您不会丢失原始策略
- **访问应用程序保护** - 自动更新应用程序以在删除之前使用保留的策略
- **更新 state.json** - 自动修复对已删除策略的引用
- **详细的日志记录** - 准确显示将要（或已经）完成什么

### 何时使用

- 发现重复的系统策略后（DockFlare-Default-*）
- 运行多个创建重复用户策略的 DockFlare 实例后
- 在主要版本升级之前清理您的 Cloudflare 帐户
- 排除策略相关问题时

### 注释

- 该实用程序需要使用有效的 Cloudflare 凭据配置 DockFlare
- 它适用于您帐户中的**所有可重复使用的策略**，而不仅仅是 DockFlare 管理的策略
- **自动处理 Access 应用程序** - 该实用程序检测使用重复策略的应用程序，将其更新为使用保留的策略，然后安全删除重复项
- **安全执行顺序** - 在删除策略之前更新应用程序，防止任何停机或访问控制间隙
- 始终首先运行 `--dry-run` 来预览更改
- 删除是永久性的且无法撤消（手动重新创建策略除外）
