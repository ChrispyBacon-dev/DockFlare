# DockFlare の仕組み

DockFlare は、Docker 環境と Cloudflare ネットワークの間に立つブリッジとして機能し、サービスを安全にインターネットへ公開する作業を自動化します。Docker ホストを継続的に監視し、Cloudflare API を使ってトンネル、DNS レコード、Access ポリシーを管理します。

## コアワークフロー

基本的な流れは、次のようなステップに分けられます。

1. **Docker イベントの監視**: DockFlare は、コンテナの `start` や `stop` などの Docker ソケットイベントを監視します。

2. **ラベルの検出**: 新しいコンテナが起動すると、DockFlare は `dockflare.` ラベルを確認します。`dockflare.enable=true` が設定されていれば、そのコンテナを管理対象として扱います。

3. **Cloudflare API との連携**: ラベルの内容に基づいて、DockFlare は Cloudflare 上に必要なリソースを構成します。
   * **Cloudflare Tunnel**: 指定された Cloudflare Tunnel に入口ルールを追加し、公開ホスト名をコンテナの内部ネットワークアドレス、たとえば `http://my-app:8080` に向けます。
   * **DNS 管理**: Cloudflare DNS ゾーンに CNAME レコードを作成し、希望する公開ホスト名、たとえば `my-app.example.com` を Cloudflare Tunnel に向けます。
   * **Access ポリシー**: アクセス制御ラベルが定義されている場合、DockFlare は再利用可能な Cloudflare Access ポリシーを作成または更新し、ID プロバイダー経由のログイン要求や公開 `bypass` の適用など、Zero Trust ルールでサービスを保護します。

4. **自動クリーンアップ**: 管理対象のコンテナが停止または削除されると、DockFlare は自動的にクリーンアップを実行します。対応する入口ルールを Cloudflare Tunnel から削除し、同じホスト名を他のサービスが使っていなければ DNS レコードと Access Application も削除します。これにより古い設定が残らず、Cloudflare 側の構成を整理できます。

## コンポーネントの概要

| コンポーネント | 役割 |
| --- | --- |
| DockFlare Master | 管理画面と API をホストし、Docker イベントを監視しながら Cloudflare Tunnel、DNS、Access ポリシーをオーケストレーションします。root 権限なしで動作し、Docker とは socket proxy 経由でのみ通信します。 |
| Docker Socket Proxy | `tecnativa/docker-socket-proxy` サイドカー。Master に最小限の Docker API（`containers`、`events` など）だけを公開し、生の Docker ソケットを直接マウントしないようにします。 |
| Redis | キャッシュ、キュー、ログストリーミング、エージェントのハートビートやバックチャネルを担当します。プライベートネットワーク `dockflare-internal` 上で動作します。 |
| DockFlare Agents（オプション） | 他ホスト上で Master の動作を再現し、Docker イベントをストリーミングで送り返しながら、自身の `cloudflared` を管理するリモートプロセスです。 |
| `cloudflared` | Master または各 Agent から Cloudflare へのトンネル接続を維持します。 |

## 階層型の構成モデル

DockFlare は、自動化と細かな制御の両方を実現するために、柔軟な階層型の構成モデルを採用しています。

1. **Docker ラベル（ベースレイヤー）**: もっとも基本となる自動化手段です。サービスのホスト名、内部サービス URL、Access ポリシーといった設定を、`docker-compose.yml` や `docker run` コマンド内で直接定義します。自動化されたサービスにとっての信頼できる情報源になります。

2. **Access Groups（抽象化レイヤー）**: 複雑なアクセスルールを複数サービスに何度も書かなくて済むよう、管理画面で再利用可能な **Access Groups** を作成できます。これは「会社のメールアドレスを許可する」「特定の国からのアクセスを許可する」といったルールをまとめたテンプレートで、名前付きの再利用可能な Cloudflare Access ポリシーに同期されます。モーダル内の Public と Authenticated の切り替えによって、DockFlare が `bypass` か `allow` のどちらを出すかが決まります。その後は `dockflare.access.group=my-policy-group` のような単一ラベルで、ポリシー全体をコンテナに適用できます。

3. **管理画面のオーバーライド（コントロールレイヤー）**: 管理画面では最も細かい制御が可能です。ダッシュボードから次のことができます。
   * ラベルまたは Access Group で定義された内容に関係なく、任意のサービスの Access ポリシーを **オーバーライド**できます。これらの変更は永続化され、コンテナの再起動でも失われません。
   * Docker 上で動作していないサービス、たとえば同じネットワーク内の別マシン上のサービス向けに **手動の入口ルールを作成**できます。
   * サービスの設定を Docker ラベルで定義された状態に **戻し**、UI 上で行ったオーバーライドを破棄できます。

この階層型モデルにより、多くのサービスは Docker ラベルだけで「設定したらあとは任せる」運用ができ、必要なときだけ管理画面で例外対応や複雑な構成に対処できます。

---

## Access ポリシーアーキテクチャ（v3.0.3+）

### 再利用可能なポリシーシステム

DockFlare は現在、Cloudflare のベストプラクティスに沿った **再利用可能なポリシーアーキテクチャ** を採用しています。

1. **Access Groups** → 同期先 → **Cloudflare Reusable Policies**
2. **Access Applications** → 参照先 → **Reusable Policy IDs**
3. **単一の信頼できる情報源** → 一度更新すれば全体に反映

このアーキテクチャによりポリシーの重複がなくなり、DockFlare と Cloudflare ダッシュボードのどちらからでも完全な双方向同期でポリシーを管理できます。

### システム管理ポリシー

DockFlare は、一貫した動作を保つために 2 つの主要ポリシーを自動管理します。

- **`public-default-bypass`**: 公開アクセス用の bypass ポリシー
  - 削除できないシステムポリシー
  - 初期化時に自動作成される
  - Cloudflare 名: `DockFlare-Default-Public-Access-Bypass`
  - 判定: `bypass`、`everyone` ルール付き
  - ゾーン保護を迂回して公開アクセスが必要なサービスで使用される
  - Cloudflare ダッシュボード内で bypass ポリシーが重複するのを防ぐ

- **`authenticated-default`**: デフォルトの認証ポリシー
  - 削除できないシステムポリシー
  - 初期化時に自動作成される
  - Cloudflare 名: `DockFlare-Default-Authenticated-Access`
  - 判定: `allow`、ワンタイム PIN とメール制限付き
  - 基本的な認証付きアクセスのシナリオで使用される

### 旧ラベルの移行

DockFlare は、従来のラベルをシステムポリシーへ自動的に移行します。

- `dockflare.access.policy=bypass` → `public-default-bypass` を使用
- `dockflare.access.group=bypass` → `public-default-bypass` を使用
- `dockflare.access.policy=authenticate` → `authenticated-default` を使用

移行はコンテナの処理とリコンシリエーションの途中で透過的に行われるため、手動作業は不要です。

### ゾーンのデフォルトポリシー

ゾーンレベルのワイルドカードポリシー（`*.domain.com`）は、優先順位によって多層的な保護を実現します。

1. **特定ホスト名のポリシー**（例: `app.example.com`）- 最優先
2. **ゾーンワイルドカードポリシー**（例: `*.example.com`）- フォールバック
3. **ポリシーなし** = Access App なしの公開アクセス - 既定動作

これにより、設定漏れや文書化されていないサービスであっても、ゾーンレベルのポリシーで保護された状態を維持できます。

**例:**
- ゾーンポリシー: `*.internal.company.com` → 会社のメールアドレスでの認証が必要
- 特定サービス: `public-demo.internal.company.com` → `public-default-bypass` を使用
- 忘れられたサービス: `test.internal.company.com` → ゾーンポリシーで保護され、認証が必要
