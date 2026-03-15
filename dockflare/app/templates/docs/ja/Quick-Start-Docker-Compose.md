# クイックスタート (Docker Compose)

このガイドでは、強化された socket proxy と rootless Master 構成で DockFlare を最短で起動する手順を説明します。

### 1. `docker-compose.yml` ファイルを作成します

以下のスタックは docker-socket-proxy を起動し、永続ボリュームに正しい所有権を設定し、Redis とともに DockFlare を起動します。

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

**注:**
- Master コンテナは `dockflare` ユーザー (UID/GID 65532) で動作します。ホスト側の権限を合わせる必要がある場合は、`DOCKFLARE_UID`/`DOCKFLARE_GID` を設定してイメージを再ビルドするか、init ジョブを調整してください。
- proxy は必須です。DockFlare は `/var/run/docker.sock` を直接マウントしません。これにより Master が到達できる Docker API の範囲を制限できます。
- 名前付きボリュームではなく bind mount を使う場合は、対象ディレクトリが UID/GID 65532 (または上書きした値) で書き込み可能であることを確認してください。
- 外部ネットワークが存在しない場合は、一度作成します: `docker network create cloudflare-net`。

### 2. DockFlare を実行する

スタックを分離モードで開始します。

```bash
docker compose up -d
```

これにより、プロキシが起動され、ボリュームが準備され、DockFlare が Redis とともに起動されます。

### 3. Pre-Flight セットアップを完了する

サービスの実行後、ブラウザを開いて `http://<your-server-ip>:5000` を表示します。

**Pre-Flight Setup Wizard** では、次の手順を実行できます。
1. 管理画面のパスワードを作成します。
2. Cloudflare 認証情報 (アカウント ID、ゾーン ID、API トークン) を入力します。
3. 初期の Cloudflare Tunnel を構成します。
4. *(オプション)* DockFlare バックアップ アーカイブからの復元。すでに `dockflare_backup_*.zip` がある場合は、ステップ 1 の前に **バックアップから復元** を選択してください。ウィザードは構成をインポートし、コンテナを自動的に再起動します。

### 4. 既存ユーザー向け（アップグレード）

古いリリースからアップグレードする場合、DockFlare は従来の `.env` ファイルを検出し、構成を暗号化ストアへ移行したうえでパスワード作成を案内します。socket proxy は引き続き必要です。`/var/run/docker.sock` の直接マウントはサポートされなくなりました。
