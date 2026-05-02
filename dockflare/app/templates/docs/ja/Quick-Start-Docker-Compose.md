# クイックスタート (Docker Compose)

このガイドでは、強化された socket proxy と rootless Master 構成で DockFlare を最短で起動する手順を説明します。

## オプション A — ワンライナーインストール（推奨）

DockFlare を最短で起動するには、[dockflare.app](https://dockflare.app) でホストされているインタラクティブなインストールスクリプトを使用します：

```bash
bash <(curl -fsSL https://dockflare.app/install.sh)
```

スクリプトは以下の手順を案内します：
1. インストールディレクトリの選択（デフォルト：`~/dockflare/`）。
2. ローカル UI ポートの選択（デフォルト：`5000`）。
3. DockFlare 自身の Cloudflare トンネルの設定（オプション）。
4. メールプロファイルの有効化（オプション）（dockflare-mail-manager + dockflare-webmail）。

その後、`docker-compose.yml` を生成し、確認を求めてからスタックを起動します。

起動後、`http://<your-server-ip>:5000` を開いてセットアップウィザードを完了してください。

---

## オプション B — 手動 Docker Compose

### 1. `docker-compose.yml` ファイルを作成します

以下のスタックは docker-socket-proxy を起動し、永続ボリュームに正しい所有権を設定し、Redis とともに DockFlare を起動します。

```yaml
services:
  docker-socket-proxy:
    image: tecnativa/docker-socket-proxy:v0.4.1
    container_name: docker-socket-proxy
    restart: unless-stopped
    logging:
      driver: "none"
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
    command: ["sh", "-c", "chown -R ${DOCKFLARE_UID:-65532}:${DOCKFLARE_GID:-65532} /app/data"]
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
      - "5000:5000" # Optional: comment out once exposed via Cloudflare Tunnel with an Access Policy to restrict access to tunnel-only
    #labels: # -- Cloudflare Tunnel Configuration (via DockFlare) OPTIONAL --
      # Main DockFlare with access policy
      #- dockflare.enable=true
      #- dockflare.hostname=dockflare.TLD  # replace with your domain
      #- dockflare.service=http://dockflare:5000
      #- dockflare.access.group=YOUR-ACCESS-GROUP-ID  # your custom access policy
      # -- OAuth Callback Path (Bypass Access Policy) OPTIONAL --
      # Required if using OAuth authentication with access policies on main interface
      #- dockflare.0.hostname=dockflare.example.tld
      #- dockflare.0.path=/auth/google/callback
      #- dockflare.0.service=http://dockflare:5000
      #- dockflare.0.access.group=public-default-bypass

      # Add additional callback paths for other OAuth providers as needed
      # - dockflare.1.hostname=dockflare.example.com
      # - dockflare.1.path=/auth/github/callback
      # - dockflare.1.service=http://dockflare:5000
      # - dockflare.1.access.group=public-default-bypass
    volumes:
      - dockflare_data:/app/data
    environment:
      - REDIS_URL=redis://redis:6379/0
      - REDIS_DB_INDEX=0
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
    logging:
      driver: "none"
    volumes:
      - dockflare_redis:/data
    networks:
      - dockflare-internal

  dockflare-mail-manager:
    image: alplat/dockflare-mail-manager:stable
    container_name: dockflare-mail-manager
    restart: unless-stopped
    profiles: ["email"]
    environment:
      - DOCKFLARE_MASTER_URL=http://dockflare:5000
      - MAIL_DATA_PATH=/data
    volumes:
      - mail_data:/data
    depends_on:
      dockflare:
        condition: service_started
    networks:
      - cloudflare-net
      - dockflare-internal

  dockflare-webmail:
    image: alplat/dockflare-webmail:stable
    container_name: dockflare-webmail
    restart: unless-stopped
    profiles: ["email"]
    environment:
      - DOCKFLARE_MASTER_URL=https://dockflare.TLD  # replace with your domain
    labels:
      - dockflare.enable=true
      - dockflare.hostname=mail.dockflare.TLD  # replace with your domain
      - dockflare.service=http://dockflare-webmail:80
    depends_on:
      dockflare-mail-manager:
        condition: service_started
    networks:
      - cloudflare-net
      - dockflare-internal

volumes:
  dockflare_data:
  dockflare_redis:
  mail_data:

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

### 2. 外部ネットワークを作成する

まだ存在しない場合：

```bash
docker network create cloudflare-net
```

### 3. DockFlare を実行する

スタックを分離モードで開始します。

```bash
docker compose up -d
```

これにより、プロキシが起動され、ボリュームが準備され、DockFlare が Redis とともに起動されます。

### 4. Pre-Flight セットアップを完了する

サービスの実行後、ブラウザを開いて `http://<your-server-ip>:5000` を表示します。

**Pre-Flight Setup Wizard** では、次の手順を実行できます。
1. 管理画面のパスワードを作成します。
2. Cloudflare 認証情報 (アカウント ID、ゾーン ID、API トークン) を入力します。
3. 初期の Cloudflare Tunnel を構成します。
4. *(オプション)* DockFlare バックアップ アーカイブからの復元。すでに `dockflare_backup_*.zip` がある場合は、ステップ 1 の前に **バックアップから復元** を選択してください。ウィザードは構成をインポートし、コンテナを自動的に再起動します。

### 5. 既存ユーザー向け（アップグレード）

古いリリースからアップグレードする場合、DockFlare は従来の `.env` ファイルを検出し、構成を暗号化ストアへ移行したうえでパスワード作成を案内します。socket proxy は引き続き必要です。`/var/run/docker.sock` の直接マウントはサポートされなくなりました。
