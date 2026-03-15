# コンテナラベルのリファレンス

DockFlare は主に、コンテナに付与した Docker ラベルで構成します。このページでは、サポートされているラベルをまとめて説明します。

## 基本構成

これらのラベルは、基本的なルーティングとサービス定義を制御します。

|ラベル |説明 |例 |
| :--- | :--- | :--- |
| `dockflare.enable` | **必須。** 有効化スイッチです。DockFlare がこのコンテナを管理するには `true` に設定する必要があります。 | `dockflare.enable=true` |
| `dockflare.hostname` | **必須。** サービスの公開ホスト名。 | `dockflare.hostname=myservice.example.com` |
| `dockflare.service` | **必須。** Cloudflare Tunnel が接続するサービスの内部 URL。`http`、`https`、`tcp`、`ssh`、`rdp`、`http_status:XXX`、`bastion` を指定できます。 | `dockflare.service=http://my-app-container:8080` |
| `dockflare.path` |このサービスにルーティングする URL パス。同じホスト名で複数のサービスを公開する場合に便利です。 | `dockflare.path=/api` |
| `dockflare.zonename` | (オプション) DNS レコードを作成する Cloudflare Zone（ドメイン）を明示指定します。省略した場合、DockFlare はホスト名から Zone を自動検出し、検出できなかった場合のみ設定済みのデフォルト（`CF_ZONE_ID`）にフォールバックします。 | `dockflare.zonename=another-domain.com` |
| `dockflare.no_tls_verify` | `true` に設定すると、`cloudflared` とオリジン サービス間の接続の TLS 証明書検証が無効になります。自己署名証明書を持つオリジンに役立ちます。 | `dockflare.no_tls_verify=true` |
| `dockflare.originsrvname` | オリジンへの TLS 接続で使用する SNI（Server Name Indication）ホスト名を指定します。Cloudflare ダッシュボードでは「Origin Server Name」として表示されます。 | `dockflare.originsrvname=internal.service.local` |
| `dockflare.httpHostHeader` | `cloudflared` からオリジン サービスに送信される `Host` ヘッダーをオーバーライドします。 | `dockflare.httpHostHeader=custom-host.internal` |
| `dockflare.http2_origin` | `true` に設定すると、`cloudflared` とオリジン サービス間の接続で HTTP/2 プロトコルが有効になります。 gRPC サービスに必要です。 HTTP/HTTPS サービスにのみ適用されます。 | `dockflare.http2_origin=true` |
| `dockflare.disable_chunked_encoding` | `true` に設定すると、HTTP/1.1 経由のチャンク転送エンコーディングが無効になります。 WSGI サーバー (Flask、Django、FastAPI) およびチャンク化されたリクエストを適切にサポートしないその他のオリジンに役立ちます。 HTTP/HTTPS サービスにのみ適用されます。 | `dockflare.disable_chunked_encoding=true` |

> **ヒント:** DockFlare v3.0 以降、多くのケースで `dockflare.zonename` は不要です。Master はホスト名のサフィックスから正しい Cloudflare Zone を検出し、見つからない場合のみデフォルト Zone にフォールバックします。意図的に別の Zone に作成したい場合だけ指定してください。

> **注:** Cloudflare の **Match SNI to Host** は、ダッシュボードの DockFlare 手動ルール設定で利用できます。現在は Docker ラベルでは設定できません。

---

## アクセスポリシーの構成

これらのラベルを使用すると、Cloudflare Access アプリケーションを動的に作成および管理して、サービスを保護できます。

**注:** ポリシー管理には **Access Groups**（`dockflare.access.group`）の利用を強く推奨します。DockFlare 3.0.3 では、Access Group を名前付きの再利用可能 Cloudflare Access Policy に同期でき、複数アプリでの再利用と双方向編集が可能になります。個別の `dockflare.access.*` ラベルは、1 回限りの例外設定向けです。`dockflare.access.group` または `dockflare.access.groups` を使う場合、他の `dockflare.access.*` は無視されます。

### v3.0.3 での重要な変更点

#### システムのデフォルト バイパス ポリシー

v3.0.3 以降、`dockflare.access.policy=bypass` または `dockflare.access.group=bypass` を使うと、インラインポリシーを作成する代わりに、システム管理の再利用可能ポリシー `public-default-bypass` を参照します。これにより Cloudflare ダッシュボードが整理されます。

- **v3.0.3 より前:** 各バイパス ルールは個別のインライン ポリシーを作成しました
- **v3.0.3+:** すべてのバイパス ルールは 1 つの正規の `public-default-bypass` ポリシーを共有します

#### 従来のラベルの移行

DockFlare は、レガシーな bypass ラベルを自動的に移行し、集中管理のシステムポリシーを使うようにします。

- `dockflare.access.policy=bypass` → `public-default-bypass` システム ポリシーを使用します
- `dockflare.access.group=bypass` → `public-default-bypass` システム ポリシーを使用します

移行はコンテナ処理や reconciliation 中に透過的に行われます。コンテナ側の変更は不要です。

#### 簡素化されたアクセス構成

複雑なアクセス要件（メール/ドメイン認証、IP allowlist など）がある場合は、次がおすすめです。

1. [**アクセス ポリシー**] ページでアクセス グループを作成します。
2. `dockflare.access.group=your-group-id` で参照します

このワークフローを推奨するため、クイック作成オプションは管理画面から削除されました。

#### ゾーンのデフォルト ポリシー ラベル

`dockflare.access.policy=default_tld` ラベルは引き続き利用でき、ゾーンの `*.domain.com` ワイルドカードポリシーから保護を継承します。ゾーンポリシーが存在しない場合、そのサービスはパブリック（Access App なし）になります。

**推奨:** セキュリティ強化のため、管理画面で全ドメインの Zone Default Policy を作成してください。

|ラベル |説明 |例 |
| :--- | :--- | :--- |
| `dockflare.access.group` | このサービスに適用する Access Group の ID。ID は DockFlare 管理画面の Access Policies ページで確認できます。 | `dockflare.access.group=internal-tools-policy` |
| `dockflare.access.groups` | 適用する Access Group ID のカンマ区切りリスト。複数ポリシーを 1 つのサービスに重ねられます。 | `dockflare.access.groups=allow-team-a,allow-admins` |
| `dockflare.access.policy` | プライマリのポリシー種別。`bypass`（パブリック）、`authenticate`（ログイン必須）、`default_tld`（`*.domain.com` ポリシーを継承）を指定できます。未設定の場合はパブリックになります。再利用するなら Access Groups を優先し、これらのラベルは例外用として使ってください。 | `dockflare.access.policy=authenticate` |
| `dockflare.access.name` | Cloudflare Access アプリケーションのカスタム名。デフォルトは `DockFlare-{hostname}` です。 | `dockflare.access.name=My Web App Access` |
| `dockflare.access.session_duration` |認証されたユーザーのセッション期間 (例: `24h`、`30m`)。デフォルトは `24h` です。 | `dockflare.access.session_duration=1h` |
| `dockflare.access.app_launcher_visible` | `true` の場合、アプリケーションが Cloudflare Access App Launcher に表示されます。 | `dockflare.access.app_launcher_visible=true` |
| `dockflare.access.allowed_idps` | 許可する Identity Provider（IdP）UUID のカンマ区切りリスト。Cloudflare Zero Trust ダッシュボードで確認できます。 | `dockflare.access.allowed_idps=uuid1,uuid2` |
| `dockflare.access.auto_redirect_to_identity` | `true` の場合、ユーザーは Cloudflare Access スプラッシュ ページではなく、IdP ログイン ページにすぐにリダイレクトされます。 | `dockflare.access.auto_redirect_to_identity=true` |
| `dockflare.access.custom_rules` | Cloudflare Access Policy のルール配列を表す JSON 文字列。複雑な 1 回限りのポリシー向けです。 | `dockflare.access.custom_rules='[{"email":{"email":"user@example.com"},"action":"allow"}]'` |

---

## 複数のドメインのインデックス付きラベル

DockFlare は、インデックス付きラベルを使って 1 つのコンテナに複数のホスト名定義を持たせられます。同一サービスの別ポートや別パスを、異なる公開ホスト名で出したいときに便利です。

インデックス付きラベルを使うには、ラベルに `0` から始まる整数を付けます。

* インデックス付きのホスト名（`<index>.hostname`）は必須です。
* 同じインデックスの他のラベル（`<index>.service`、`<index>.path` など）は、そのホスト名に対するベース（非インデックス）ラベルを上書きします。
* インデックス側にラベルがない場合は、対応するベースラベルの値が使われます。

### 例

この例では、1 つのコンテナから 2 つのホスト名を公開します。
1. `app.example.com` は、ポート `80` のメイン Web インターフェイスにルーティングします。
2. `api.example.com` はポート `3000` 上の API にルーティングされ、特定のアクセス グループで保護されます。

```yaml
services:
  my-multi-service:
    image: my-app
    labels:
      - "dockflare.enable=true"

      # --- Definition 0 ---
      - "dockflare.0.hostname=app.example.com"
      - "dockflare.0.service=http://my-multi-service:80"

      # --- Definition 1 ---
      - "dockflare.1.hostname=api.example.com"
      - "dockflare.1.service=http://my-multi-service:3000"
      - "dockflare.1.access.group=api-access-policy"
```
