# 管理画面の使い方

DockFlare の管理画面は、サービスの管理、監視、設定を行うための中核ツールです。単純な Docker ラベル設定だけでは扱いにくい作業も、わかりやすいインターフェースで操作できます。

## ダッシュボード（メインページ）

ログイン後に最初に表示されるのがメインダッシュボードです。ここでは、管理中のすべてのサービスの状態をまとめて確認できます。

* **「Managed Ingress Rules」テーブル:** Docker コンテナ由来のルールでも、手動で追加したルールでも、DockFlare が管理しているすべての入口ルールが表示されます。
    * **Hostname:** 公開ホスト名
    * **Service:** 内部の接続先 URL
    * **Source:** ルールが `Docker` 由来か、管理画面で `Manually` 作成されたかを示します
    * **Status:** `active`、`pending_deletion`、`UI Override` などの状態を表示します
    * **Access:** 適用されている Access Group とモードバッジを表示します。再利用可能なポリシーが同期されると、`Public` や `Authenticated` のラベル、継承されたグループ名、Cloudflare ダッシュボードへのクイックリンクも表示されます
    * **Manage Rule:** 任意のルールを編集できます
* **リアルタイムログ:** テーブルの下には DockFlare バックエンドのログをストリーミング表示するログビューアがあり、デバッグに役立ちます。

## ルールの管理

管理画面を使うと、入口ルールを細かく管理できます。

* **「Add Manual Rule」:** このボタンを使うと、Docker で動いていないサービス（たとえば LAN 内の別ホスト上のサービス）向けに入口ルールを作成できます。フォームでは hostname、service URL、必要に応じて Access Group を指定できます。
* **「Edit any Rule」:** 各ルールの横にある **Manage Rule** をクリックすると、設定を変更できるモーダルが開きます。Docker ラベルから作られたルールに管理画面オーバーライドを適用する場合もここで行います。
* **「Revert to Labels」:** Docker 由来のルールに UI Override がある場合、**Revert to Labels** ボタンが表示されます。これを使うと手動変更を破棄し、再び Docker ラベル側の設定に戻せます。

## アクセス ポリシー ページ

このページは、再利用可能な **Access Groups** を管理し、ワイルドカードポリシーで DNS ゾーンを保護するための中心画面です。

### 高度なアクセス ポリシー

Access Groups セクションでは、次の操作ができます。
* **Create:** 2 タブ構成のモーダル（Authenticated / Public）を使って新しい Access Group を作成できます。タブごとに案内バナーが切り替わるため、DockFlare が Cloudflare の `allow` と `bypass` をどう使い分けるか把握しやすくなっています。
* **Edit:** 既存の Access Group を編集できます。モーダルではモードごとの検証が行われ、Authenticated ではメールアドレス必須、Geo/IP 設定は両モードで表示されます。
* **Delete:** 使っていない Access Group を削除できます。ただし `public-default-bypass` などのシステムポリシーは削除できません。
* **Sync from Cloudflare:** Cloudflare 側にある再利用可能ポリシーを取り込みます。
* 各エントリのアクションメニューから、Cloudflare アイコンを使って対応するポリシーを Cloudflare ダッシュボードで直接開けます。

**注意:** `public-default-bypass` は DockFlare が自動作成・自動管理するシステムポリシーです。`Bypass` アクセスを使うすべてのサービスがこの 1 つのポリシーを参照するため、Cloudflare ダッシュボードを整理しやすくなります。

### Zone Default Policies（`*.tld` ワイルドカード）

2 つ目のセクションでは、すべてのサブドメインを保護する **Zone Default Policies** を設定できます。

* **Protection Status:** ワイルドカード `*.domain.com` ポリシーを持つ DNS ゾーンには保護済みバッジ（🛡️）、未設定のゾーンには未保護バッジ（⚠️）が表示されます。
* **Create Zone Policy:** 未保護のゾーンで **Create Policy** をクリックすると、ワイルドカード Access Application を作成できます。
* **Select Policy:** そのゾーン配下のすべてのサブドメインを保護する Access Group を選びます。Public bypass、Authenticated、または任意のカスタムポリシーを使えます。
* **Security Safety Net:** 個別サービスにポリシーを付け忘れても、ゾーンレベルのワイルドカードポリシーが保護を補完します。

**ベストプラクティス:** すべてのドメインに Zone Default Policy を設定してください。公開向けドメインにはデフォルトの bypass ポリシー、内部向けドメインには認証ポリシーを使うのが基本です。これにより、サブドメインの意図しない公開を防げます。

詳細については、[アクセス ポリシーのベスト プラクティスと例](Access-Policy-Best-Practices.md) ガイドを参照してください。

## 設定ページ

設定ページには、さまざまな管理オプションと構成項目があります。

* **Cloudflare Tunnels:** アカウント内で見つかった Cloudflare Tunnel、その状態、接続されている `cloudflared` エージェントの一覧を表示します。任意のトンネルを向いている CNAME レコードも確認できます。
* **Backup & Restore:** 暗号化設定、エージェントキー、状態を含む完全な DockFlare バックアップアーカイブ（`.zip`）をダウンロードしたり、過去にエクスポートしたアーカイブをアップロードして復元したりできます。
* **セキュリティ:**
    * **Change Password:** 管理画面のパスワードを変更します。
    * **Disable Password Login:** DockFlare を別の認証プロキシの背後に置く高度な構成向けです。**⚠️ 警告:** これは Docker ネットワーク露出によるセキュリティリスクを生みます。同じ Docker ネットワーク上のコンテナは外部認証を迂回し、DockFlare API に直接アクセスできる可能性があります。シングルサインオンが必要な場合は、代わりに OAuth/OIDC プロバイダーの利用を強く推奨します。詳細は [管理画面へのアクセス](Accessing-the-Web-UI.md) を参照してください。
* **Cloudflare Credentials:** 初期設定後でも Cloudflare Account ID と API Token を更新できます。
* **Core Configuration:** Tunnel Name や Rule Grace Period などの設定を変更できます。
