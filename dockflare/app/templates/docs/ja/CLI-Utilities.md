# DockFlare CLI ユーティリティ

## 重複ポリシーのクリーンアップ

DockFlare には、Cloudflare アカウント内で重複している再利用可能ポリシーを検出し、整理するための CLI ユーティリティが含まれています。

### 問題

複数の DockFlare インスタンス（ローカル環境と本番環境など）を使っていたり、インスタンス間で `state.json` の内容がずれていたりすると、同じ名前のポリシーが Cloudflare 側に重複して作成されることがあります。このユーティリティは、最も古いポリシーを残し、それ以外の重複を削除して整理します。

### 使用法

#### プレビュー（dry run）- 最初に実行することを推奨

```bash
docker exec dockflare python -m app.cli cleanup-duplicate-policies --dry-run
```

これにより、次の内容を確認できます。
- Cloudflare アカウント内の再利用可能ポリシーをすべてスキャンする
- 名前が重複しているポリシーを特定する
- 削除対象になるポリシー（新しい方）を表示する
- 保持されるポリシー ID（最も古いもの）を表示する
- `state.json` に対して行われる更新内容を表示する
- **実際の変更は加えない**

#### クリーンアップを実行する

```bash
docker exec dockflare python -m app.cli cleanup-duplicate-policies --apply
```

これにより、次の処理が実行されます。
- 重複ポリシーを削除する（最も古いポリシーは保持）
- `state.json` を更新し、正しいポリシー ID を参照するようにする
- **実際に Cloudflare アカウントへ変更を加える**

### このユーティリティが行うこと

1. Cloudflare アカウントから **すべての再利用可能ポリシーを取得**
2. **ポリシー名ごとにグループ化**して重複を検出
3. **作成日時で並べ替え**、各名前について最も古いポリシーを保持
4. **Access Applications を確認**し、重複ポリシーを使っているアプリを特定
5. **更新して削除** - 重複ごとに次を実施
   - 影響を受けるアプリを、保持対象のポリシー ID を使うよう更新
   - その後で重複ポリシーを削除
6. **`state.json` を更新**し、すべての Access Groups が正しいポリシー ID を参照するようにする

### 出力例

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

### 安全機能

- **デフォルトで dry run** - 変更を加えるには明示的に `--apply` が必要
- **最も古いポリシーを保持** - 元のポリシーを残せる
- **Access Applications を保護** - 削除前に保持対象ポリシーへ自動更新する
- **`state.json` を更新** - 削除済みポリシーへの参照を自動修正する
- **詳細なログ** - 何を実行するか、または実行したかを明確に示す

### 使うタイミング

- 重複したシステムポリシー（`DockFlare-Default-*`）を見つけたとき
- 複数の DockFlare インスタンス運用によって重複ポリシーが発生したとき
- 大きなバージョンアップ前に Cloudflare アカウントを整理したいとき
- ポリシー関連の不具合を調査しているとき

### 注記

- このユーティリティを使うには、DockFlare に有効な Cloudflare 認証情報が設定されている必要があります
- DockFlare 管理下のポリシーだけでなく、アカウント内の **すべての再利用可能ポリシー** を対象に動作します
- **Access Applications を自動処理** - 重複ポリシーを使っているアプリを検出し、保持対象ポリシーに切り替えたうえで安全に重複を削除します
- **安全な実行順序** - 先にアプリを更新し、その後でポリシーを削除するため、ダウンタイムやアクセス制御の抜けを防げます
- 変更内容を確認したい場合は、必ず最初に `--dry-run` を実行してください
- 削除は永続的で、手動で再作成しない限り元に戻せません
