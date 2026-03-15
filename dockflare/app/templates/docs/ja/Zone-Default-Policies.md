# Zone Default Policies（ワイルドカード保護）

## 概要

Zone Default Policies は、Cloudflare Access のワイルドカードアプリケーション（`*.domain.com`）を使って、DNS Zone 配下のすべてのサブドメインを自動的に保護するためのベストプラクティス機能です。

## これで解決する問題

Zone Default Policy を設定していない場合:
- 設定し忘れたサービスが公開される
- 新しいサブドメインは手動で設定するまで無防備になる
- ホスト名設定のタイプミスがアクセス制御の抜けにつながる
- ドキュメントや運用手順のずれがセキュリティギャップになる

## 仕組み

### ポリシーの優先順位

Cloudflare は Access Policy を次の順で評価します。

1. **完全一致（Exact hostname match）**（例: `app.example.com`）
2. **ワイルドカード一致（Wildcard match）**（例: `*.example.com`）
3. **一致なし** = パブリックアクセス（Access App なし）

### DockFlareの実装

DockFlare の **Zone Default Policies** セクションでは次ができます。
- Cloudflare DNS Zones の一覧表示
- バッジによる保護ステータスの表示
- `*.zone.com` ポリシーのワンクリック作成
- Zone を保護する Access Group の選択

## セットアップガイド

### ステップ 1: ゾーンを確認する

1. **アクセス ポリシー** ページに移動します
2. **ゾーンのデフォルト ポリシー (*.tld ワイルドカード)** までスクロールします。
3. 保護ステータスを確認します。
   - 🛡️ **緑色「保護」** - ゾーンにはワイルドカード ポリシーがあります
   - ⚠️ **黄色「保護されていません」** - ゾーンは脆弱です

### ステップ 2: ゾーン ポリシーを作成する

保護されていないゾーンごとに次のようにします。

1. **ポリシーの作成** をクリックします。
2. モーダルに `*.zone-name.com` のホスト名が表示されます。
3. 適切な Access Policy（Access Group）を選択します。
   - **パブリックゾーン** → `public-default-bypass`
   - **内部ゾーン** → 認証ポリシー
   - **混合ゾーン** → 最も制限的なポリシー
4. [**ゾーン ポリシーの作成**] をクリックします。

### ステップ 3: Cloudflare で確認する

1. Cloudflare Zero Trust ダッシュボードを開きます。
2. **Access → Applications** に移動します。
3. `Zone Default: *.domain.com` という名前のアプリケーションを探します。
4. ポリシー設定が想定どおりか確認します。

## セキュリティに関する推奨事項

### 実稼働環境

✅ **Zone Default Policy を常に有効にする**
- 意図しない公開を防げる
- 設定ミスに気付きやすい
- サブドメイン探索のリスクを下げられる

### ポリシー選択戦略

- **パブリック コンテンツ ドメイン** (ブログ、マーケティング): `public-default-bypass`
- **内部ツール ドメイン**: 電子メール/ドメイン認証
- **機密データ ドメイン**: MFA 対応認証
- **開発ドメイン**: 最も厳格なポリシーによるロックダウン

### モニタリング

定期的に確認してください。
- どの Zone が保護されているか（**アクセス ポリシー** ページ）
- Cloudflare 側の Access Application ログ
- アクティブなサブドメインと、設定済みポリシーの対応

## トラブルシューティング

### 「ポリシーはすでに存在します」エラー

`*.domain.com` Access アプリケーションはすでに存在します。これは次のようなものです。
- Cloudflareで手動で作成
- 以前にDockFlareによって作成されました
- 別のツールで作成されたもの

**解決策:** Cloudflare 側でそのアプリを直接管理するか、DockFlare 経由で削除して再作成します。

### 認証なしでもサービスにアクセス可能

ポリシーの優先順位を確認します。
1. サービスに特定のホスト名ポリシーがあることを確認する
2. ゾーンのワイルドカードが存在し、正しく構成されていることを確認します
3. ゾーン保護にもかかわらずサービスをパブリックにする必要がある場合は、`dockflare.access.group=public-default-bypass` ラベルを追加します

### パブリックサービスを Zone 保護の対象外にする（bypass）

Zone レベルで認証ポリシーを適用しているが、特定サービスだけはパブリックのままにしたい場合:

1. バイパス ラベルをコンテナに追加します。
   ```yaml
   labels:
     - "dockflare.access.group=public-default-bypass"
   ```
2. これにより、対象ホスト名に対して `bypass` 判定の Access Application が作成されます。
3. 完全一致のホスト名ポリシーが、ワイルドカードポリシーより優先されます。
4. Zone は保護されたまま、対象サービスだけをパブリックにできます。

### ゾーンがリストに表示されない

考えられる原因:
- DNS ゾーンが Cloudflare アカウントにありません
- API トークンに `Zone:Zone:Read` 権限がありません
- ゾーンが一時停止または削除されている

**解決策:** Cloudflare ダッシュボードにゾーンが存在し、API トークンに正しい権限があることを確認してください。

## ベストプラクティス

1. **最初にゾーン ポリシーを作成します** - サービスを追加する前に
2. **内部ゾーンには認証を使用します** - バイパスは決して使用しないでください
3. **例外を文書化** - ゾーンに保護が必要ない場合は、その理由を文書化します。
4. **定期的な監査** - ゾーンの保護ステータスの月次レビュー
5. **本番前のテスト** - ワイルドカード ポリシーが既存のサービスを中断しないことを確認します
6. **最小特権の原則** - 正当なアクセスを許可しながら、最も制限的なポリシーを使用します。

## 構成例

### パブリック ブログ ゾーン
```
Zone: blog.example.com
Policy: public-default-bypass
Result: All subdomains publicly accessible (*.blog.example.com)
```

### 内部ツールゾーン
```
Zone: internal.company.com
Policy: Company Email Authentication
Result: All subdomains require @company.com email (*.internal.company.com)
```

### 混合の開発 Zone
```
Zone: dev.company.com
Policy: Developer Team Authentication
Result: All dev services protected by default (*.dev.company.com)
Specific overrides: public-demo.dev.company.com → public-default-bypass
```

## ポリシーの優先順位を理解する

### シナリオ 1: 特定のポリシーがワイルドカードをオーバーライドする

**セットアップ:**
- ゾーンポリシー: `*.example.com` → 認証が必要です
- 特定のポリシー: `blog.example.com` → `public-default-bypass`

**結果:**
- `blog.example.com` → パブリック (特定のポリシーが優先)
- `api.example.com` → 認証が必要です (ワイルドカードがキャッチします)
- `forgotten.example.com` → 認証が必要です (ワイルドカードがキャッチします)

### シナリオ 2: セーフティ ネットとしてのワイルドカード

**セットアップ:**
- ゾーンポリシー: `*.internal.company.com` → @company.com の電子メールが必要です
- 特定のポリシー: `test-server.internal.company.com` にはなし

**結果:**
- `test-server.internal.company.com` → 認証が必要です (ワイルドカードで保護されています)
- 設定を忘れた場合でも、ゾーンポリシーによって保護されます

### シナリオ 3: 保護がない

**セットアップ:**
- ゾーン ポリシー: `*.risky-domain.com` にはなし
- 特定のポリシー: `app.risky-domain.com` → 認証

**結果:**
- `app.risky-domain.com` → 認証が必要です (特定のポリシー)
- `forgotten.risky-domain.com` → ⚠️ **PUBLIC** (キャッチするワイルドカードなし)

## DockFlare ラベルとの統合

### `default_tld` ラベルの使用

`dockflare.access.policy=default_tld` ラベルは、DockFlare にゾーンのワイルドカード ポリシーを使用するように指示します。

```yaml
services:
  my-service:
    image: nginx
    labels:
      - "dockflare.enable=true"
      - "dockflare.hostname=new-app.internal.company.com"
      - "dockflare.service=http://my-service:80"
      - "dockflare.access.policy=default_tld"
```

**動作:**
- `*.internal.company.com` が存在する場合 → そのポリシーを継承します
- ゾーンポリシーが存在しない場合 → サービスはパブリック (Access App は作成されていない)

### 推奨事項

`default_tld` ラベルに依存する代わりに:
1. UI でゾーンのデフォルト ポリシーを作成する
2. ワイルドカード ポリシーですべてのサービスを自動的に保護する
3. 例外に対して特定のポリシーのみを作成する

これにより、デフォルトでセキュリティが強化されます。

## 関連ドキュメント

- [アクセス ポリシーのベスト プラクティス](Access-Policy-Best-Practices.md)
- [管理画面の使い方](Using-the-Web-UI.md)
- [コンテナラベル](Container-Labels.md)
- [DockFlareの仕組み](How-DockFlare-Works.md)
- [セキュリティアーキテクチャ](Security-Architecture.md)
