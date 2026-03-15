# 複数のドメインの使用 (インデックス付きラベル)

DockFlare には **インデックス付きラベル（indexed labels）** という機能があり、1 つのコンテナに対して複数の独立した入口ルールを定義できます。同一サービスの別ポートや別パスを、異なる公開ホスト名で公開したい場合に便利です。

## 仕組み

複数ルールを作るには、通常の DockFlare ラベルの先頭に `0` から始まる整数とドットを付けます。たとえば `dockflare.0.hostname`、`dockflare.1.hostname` のように指定します。

* 各インデックス（`0`、`1`、`2` など）は個別の入口ルールを表します。
* 新しいルールには、インデックス付きホスト名（`dockflare.<index>.hostname`）が必須です。
* 同じインデックスの他のラベル（`dockflare.<index>.service` など）は、そのルールにのみ適用されます。

## フォールバック メカニズム

インデックス付きラベルの重要な特徴がフォールバックです。特定ルールにインデックス付きラベルがない場合、**対応するベース（非インデックス）ラベルの値**が使われます。

これにより、共通設定はベースで 1 度だけ定義し、ルールごとに差分だけ上書きできます。

## 例: 管理画面と API の公開

ポート `80` の Web アプリと、ポート `3000` の別 API を同じコンテナで提供しているとします。`app.example.com` と `api.example.com` で公開し、メインアプリはパブリックのまま、API は Access Group で保護したいケースです。

インデックス付きラベルを使用してこれを構成する方法は次のとおりです。

```yaml
services:
  my-app:
    image: my-application
    restart: unless-stopped
    networks:
      - cloudflare-net
    labels:
      - "dockflare.enable=true"

      # --- Base Labels (Fallback) ---
      # This service is used by rule 0, as it's not specified there.
      - "dockflare.service=http://my-app:80" 

      # --- Rule 0: The main web app ---
      - "dockflare.0.hostname=app.example.com"
      # No 'service' label here, so it falls back to the base one.
      # No 'access.group' label, so it's public.

      # --- Rule 1: The API ---
      - "dockflare.1.hostname=api.example.com"
      # Override the service to point to the API port.
      - "dockflare.1.service=http://my-app:3000"
      # Add a specific access policy for this rule only.
      - "dockflare.1.access.group=api-users-policy"
```

### 例の内訳

* **ルール 0 (`app.example.com`)**:
    * `dockflare.0.hostname` を定義します。
    * `dockflare.0.service` が定義されていないため、ベースの `dockflare.service` にフォールバックし、`http://my-app:80` を使用します。
    * このインデックスまたは基本レベルにはアクセス ポリシーが定義されていないため、これはパブリック サービスです。

* **ルール 1 (`api.example.com`)**:
    * `dockflare.1.hostname` を定義します。
    * `dockflare.1.service` でサービスを**オーバーライド**し、API ポート `3000` を指します。
    * `dockflare.1.access.group` を使用して特定のセキュリティ ポリシーを適用します。このラベルはこのルールにのみ影響します。

この構成にすると、ラベル設定が整理され、繰り返しも減るため、`docker-compose.yml` の可読性と保守性が上がります。
