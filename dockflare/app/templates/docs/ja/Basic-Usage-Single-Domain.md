# 基本的な使い方（単一ドメイン）

このガイドでは、DockFlare の最も一般的な使い方として、単一の Docker コンテナを公開ホスト名でインターネットに公開する手順を説明します。

## 前提条件

始める前に、次のものが揃っていることを確認してください。
1. [クイック スタート](Quick-Start-Docker-Compose.md) ガイドを完了します。
2. DockFlare が実行されており、Cloudflare アカウントに接続されています。
3. 公開したいサービスがあります (この例では `nginx` を使用します)。

## 例: NGINX コンテナの公開

標準の NGINX Web サーバーをホスト名 `nginx.example.com` で公開したいとします。

### 1. サービスを `docker-compose.yml` に追加します

`docker-compose.yml` ファイルを変更して、`nginx` サービスを含めます。重要なのは、構成に `dockflare.*` ラベルを追加することです。

```yaml
version: '3.8'

services:
  docker-socket-proxy:
    image: tecnativa/docker-socket-proxy:v0.4.1
    container_name: docker-socket-proxy
    restart: unless-stopped
    environment:
      - DOCKER_HOST=unix:///var/run/docker.sock
      - CONTAINERS=1
      - EVENTS=1
      - NETWORKS=1
      - IMAGES=1
      - POST=1
      - PING=1
      - INFO=1
      - EXEC=1
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock
    networks:
      - dockflare-internal

  dockflare-init:
    image: alpine:3.20
    command: ["sh", "-c", "chown -R 65532:65532 /app/data"]
    volumes:
      - dockflare_data:/app/data
    networks:
      - dockflare-internal
    restart: "no"

  dockflare:
    image: alplat/dockflare:stable
    container_name: dockflare
    restart: unless-stopped
    ports:
      - "5000:5000"
    volumes:
      - dockflare_data:/app/data
    environment:
      - REDIS_URL=redis://redis:6379/0
      - REDIS_DB_INDEX=0  # Optional: specify Redis database index (0-15) for isolation from other containers
      - DOCKER_HOST=tcp://docker-socket-proxy:2375
    depends_on:
      docker-socket-proxy:
        condition: service_started
      dockflare-init:
        condition: service_completed_successfully
      redis:
        condition: service_started
    networks:
      - cloudflare-net
      - dockflare-internal

  # Add your new service here
  nginx-webserver:
    image: nginx:latest
    container_name: my-nginx
    restart: unless-stopped
    networks:
      - cloudflare-net
    labels:
      - "dockflare.enable=true"
      - "dockflare.hostname=nginx.example.com"
      - "dockflare.service=http://nginx-webserver:80"
      # Optional: Apply public access with zone protection bypass
      - "dockflare.access.group=public-default-bypass"

  redis:
    image: redis:7-alpine
    container_name: dockflare-redis
    restart: unless-stopped
    command: ["redis-server", "--save", "", "--appendonly", "no"]
    volumes:
      - dockflare_redis:/data
    networks:
      - dockflare-internal

volumes:
  dockflare_data:
  dockflare_redis:

networks:
  cloudflare-net:
    name: cloudflare-net
    external: true
  dockflare-internal:
    name: dockflare-internal
```
> **なぜ Redis が必要ですか?** DockFlare はキャッシュ、ログストリーミング、クロススレッドのメッセージングに Redis を使います。プライベートな `dockflare-internal` ネットワーク上で動かすことで、Redis には DockFlare だけが到達でき、ワークロードは `cloudflare-net` で分離されたままになります。


### 2. ラベルを理解する

* `dockflare.enable=true`: DockFlare にこのコンテナを管理させます。
* `dockflare.hostname=nginx.example.com`: サービスを公開するホスト名です。DockFlare は Cloudflare DNS にこのホスト名のレコードを作成します。
* `dockflare.service=http://nginx-webserver:80`: Cloudflare Tunnel が転送する先（オリジン）です。これは NGINX コンテナの内部アドレスで、同一 Docker ネットワーク内でサービス名（`nginx-webserver`）を名前解決できることを前提としています。
* `dockflare.access.group=public-default-bypass`: (オプション) ゾーンレベルの `*.example.com` 保護ポリシーがあっても、対象サービスをパブリックのままにするためのシステム bypass ポリシーです。

### 3. サービスをデプロイする

`docker-compose.yml` ファイルを保存し、次のコマンドを実行して新しいサービスを開始します。

```bash
docker compose up -d
```

### 4. 検証

DockFlare は新しいコンテナを検出し、次のアクションを自動的に実行します。
1. `nginx.example.com` の Cloudflare Tunnel に入口ルールを追加します。
2. Cloudflare DNS で、トンネルを指す `nginx.example.com` の CNAME レコードを作成します。

これはいくつかの方法で確認できます。
* **DockFlare 管理画面**: `nginx.example.com` サービスがダッシュボードに表示されます。
* **Cloudflare ダッシュボード**: DNS 設定に新しい CNAME レコードが表示され、トンネル設定に新しい入口ルールが表示されます。

DNS が伝播したら、ブラウザーで `https://nginx.example.com` にアクセスし、デフォルトの NGINX のようこそページが表示されることを確認してください。

## バックアップと復元の詳細

DockFlare にはバックアップ/復元フローが組み込まれているため、インスタンスを数分で移行または復旧できます。

### バックアップ アーカイブの内容

**設定 → バックアップと復元**（またはオンボーディングウィザード）からバックアップをダウンロードすると、DockFlare は次のファイルを含む `.zip` を生成します。

|ファイル |説明 |
| --- | --- |
| `dockflare_config.dat` |暗号化された設定ペイロード（Cloudflare 認証情報、管理画面のパスワードハッシュ、トンネルのデフォルト、Master API キーなど）。 |
| `dockflare.key` | `dockflare_config.dat` およびその他の暗号化されたペイロードを復号化するために使用される Fernet キー。アーカイブと一緒に保管してください。 |
| `agent_keys.dat` |エージェント API キー、メタデータ、失効ステータスの暗号化されたレジストリ。 |
| `state.json` |実行時状態のプレーンな JSON スナップショット (管理対象ルール、エージェント、アクセス グループ)。これは、オペレーターが必要に応じて特定の部分を検査または移行できるように含まれています。 |
| `manifest.json` |アーカイブ内の各ファイルのチェックサムとバージョン情報。 |

バックアップは自己完結型です。ウィザード/Apply エンドポイント経由で復元すると、各ファイルが `/app/data/` に書き込まれ、直ちにコンテナ再起動がスケジュールされるため、暗号化設定が起動時に読み込まれます。

### 復元と互換性に関する注意事項

- **ウィザードと Settings UI**: `.zip` をアップロードすると、DockFlare がインポートして状態をリロードし、その後終了します。Docker がコンテナを自動再起動するため、手動介入なしで運用状態に戻ります。
- **レガシー `state.json`**: トラブルシューティングや高度なワークフローでは、`state.json` のみをアップロードできます。DockFlare はランタイム状態を反映しますが、暗号化設定は復元されないため、認証情報の再入力が必要です。
- **自動**: 再起動は自動で行われます。リバースプロキシのヘルスチェックは、復元後の短い再起動ウィンドウ (~5 秒) を許容するようにしてください。

バックアップには Redis のデータセットは**含まれません**。Redis は DockFlare が再計算できるデータのみをキャッシュします。アーカイブとあわせて `/app/data` ボリュームを安全に保護し、バックアップしてください。
