# DockFlare エージェントとマルチサーバーアーキテクチャ

DockFlare 3.0 では、複数の Docker ホストにまたがって Cloudflare Tunnel を管理できる分散実行モデルが導入されています。DockFlare の **Master** が構成を調整し、軽量な **エージェント** がワークロードのそばで動作して各ホストの `cloudflared` を Master と同期します。

このガイドでは、エージェントをデプロイするためのアーキテクチャ、セキュリティモデル、段階的なワークフローについて説明します。

---

## なぜエージェントなのか？

* **実行環境と入口の分離** – 単一のコントロールプレーンを維持しつつ、ワークロードをユーザーの近くに配置できます。
* **ホスト単位の可視性** – エージェントごとのハートビート、トンネル状態、コマンド履歴を監視できます。
* **最小権限のトークン** – 侵害されたエージェントだけを失効させ、Master や他ホストへの影響を最小化します。
* **堅牢な更新** – Master が一時的に利用できなくても、エージェントは最後に取得した構成でトラフィックを処理し続けます。

---

## コンポーネントの概要

| コンポーネント | 役割 |
|-----------|----------------|
| **Master (DockFlare)** | 管理画面をホストし、状態を保存し、必要な入口ルールを調整し、コマンドを発行します。 |
| **Redis** | キャッシュ、エージェントのハートビート、キューに入ったコマンドを扱うバックプレーンです。 |
| **DockFlare エージェント** | ローカルの Docker イベントを監視し、コマンドを実行し、`cloudflared` を動かすヘッドレスコンテナです。 |
| **cloudflared** | エージェントごとに Cloudflare への実際のトンネル接続を処理します。 |

通常、Master と Redis は同じ場所で動作し、エージェントはワークロードの近く（場合によってはリモートネットワーク上）で動作します。

---

## 前提条件

* Redis を構成した DockFlare Master v3.0 以降（`REDIS_URL` が設定されていること）。必要に応じて `REDIS_DB_INDEX` を指定し、同じ Redis インスタンスを使う他コンテナからデータを分離します。
* Tunnel + Access 権限を持つ Cloudflare API トークン（以前のバージョンと同様）。
* 管理する予定のすべてのホスト上の Docker ランタイム。
* （オプション）Master を公開しない場合は、Master とエージェント間の専用ネットワークセグメントまたは VPN。

---

## ワークフローの概要

1. DockFlare 管理画面（`Agents → Generate Key`）で **Agent API キー** を生成します。
2. リモートホストに **DockFlare エージェント** コンテナをデプロイし、Master URL とキーを渡します。
3. エージェントが Master に **登録**され、ステータスが *Pending* として表示されます。
4. Master の管理画面でエージェントを **承認** し、そのホストに Cloudflare Tunnel を割り当てるか作成します。
5. Master はコマンドをキューに入れます。エージェントは **ポーリング** して設定を適用し、状態とハートビートを報告します。DockFlare はホスト名ごとに対象ゾーンを自動検出します（検出に失敗した場合のみデフォルトゾーンにフォールバックします）。
6. エージェントホスト上でコンテナが起動または停止すると、エージェントがイベントを Master にストリーミングし、DNS、Access ポリシー、Tunnel の入口ルールを更新します。

---

## DockFlare Agent のデプロイ

> ℹ️ エージェントは `alplat/dockflare-agent` として公開されます。パブリックリポジトリが公開されるまでは、DockFlare 3.0 に含まれる `DockFlare-agent` ソースツリーからビルドできます。

```bash
# Example environment file used by the agent container
DOCKFLARE_MASTER_URL=https://dockflare.example.com
DOCKFLARE_API_KEY=agent_api_key_goes_here
DOCKER_HOST=tcp://docker-socket-proxy:2375
# control the docker image used for the managed cloudflared tunnel (accepts repo:tag or repo@sha256:<digest>)
CLOUDFLARED_IMAGE=cloudflare/cloudflared:2025.9.0
LOG_LEVEL=info
TZ=Europe/Zurich
```

Agent ホスト上の最小限の `docker-compose.yml`:

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
      - EXEC=1
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock
    networks:
      - dockflare-internal
      
  dockflare-agent:
    image: alplat/dockflare-agent:latest
    container_name: dockflare-agent
    restart: unless-stopped
    env_file:
      - .env
    environment:
      - DOCKER_HOST=${DOCKER_HOST:-tcp://docker-socket-proxy:2375}
      - TZ=${TZ:-UTC}
      - LOG_LEVEL=${LOG_LEVEL:-info}
    volumes:
      - agent_data:/app/data
    depends_on:
      - docker-socket-proxy
    networks:
      - cloudflare-net
      - dockflare-internal

volumes:
  agent_data:

networks:
  cloudflare-net:
    name: cloudflare-net
    external: true
  dockflare-internal:
    name: dockflare-internal
```

- `docker network create cloudflare-net` を 1 回実行して、Master とエージェントが使う共有ネットワークを作成します。
- socket proxy は、エージェントが到達できる Docker API の範囲を制限します。`1` に設定した機能だけが公開されます。
- エージェントイメージは特権のない `dockflare` ユーザー（UID/GID 65532）として実行されます。`/app/data` などのマウント先がそのアカウントで書き込み可能であることを確認するか、ホストに合わせるために `DOCKFLARE_UID/DOCKFLARE_GID` を使って再ビルドしてください。
- `.env` に `DOCKFLARE_MASTER_URL` と `DOCKFLARE_API_KEY` を設定します。`LOG_LEVEL` や `DOCKER_HOST` などの上書きも同じ方法で指定できます。

---

## セキュリティモデル

* **Master API キー** – 管理 API を保護します。管理画面では `Show Master API Key` をクリックした後にのみ表示されます。
* **Agent API キー** – エージェントごとに一意です。キーを取り消すと、そのホストからの以後の登録やコマンドが即座にブロックされます。
* **Redis** – キューとキャッシュに使用されます。信頼できる LAN の外部で実行している場合は、パスワードやネットワーク ACL で保護してください。
* **トランスポート** – エージェントの通信が暗号化されるように、Master は HTTPS の背後で運用してください（例: Cloudflare Access 経由）。
* **最小特権ランタイム** – エージェントコンテナは `dockflare` ユーザー（UID/GID 65532）として実行され、socket proxy によって Docker アクセスの範囲をコンテナ検査とライフサイクル制御に限定します。

### 推奨されるハードニング

1. Agent キーをシークレットストアやパスワードマネージャーに保管し、定期的にローテーションします。
2. **パスワードログインを無効にしないでください** - 代わりに OAuth/OIDC で SSO を有効にしてください。どうしても無効にする場合は、同一 Docker ネットワーク上のコンテナが外部認証を迂回できるリスクがある点を理解してください。詳細は [管理画面へのアクセス - パスワードログインの無効化](Accessing-the-Web-UI.md) を参照してください。
3. 権限の分離を強めるには、エージェントごとに個別のトンネルを使用します。
4. `Agents` ページでハートビートの欠落を監視します。オフラインノードは管理画面から直接削除できます。

---

## トラブルシューティング

| 症状 | 対処 |
|---------|------|
| status が `pending` のまま | 正しい API キーで登録されていることを確認し、管理画面から承認してください。 |
| コマンドが消化されない | Redis 接続と、エージェントコンテナの時刻同期を確認します。 |
| DNS が更新されない | Master が Cloudflare に到達でき、エージェントがコンテナイベントを送信できている必要があります。`docker logs dockflare-agent` を確認してください。 |
| ハートビートが offline | エージェントと Master 間のネットワーク経路を確認します。一般的な原因はファイアウォールや TLS の問題です。 |

---

## 次のステップ

* リポジトリの README で更新されたクイックスタートを確認し、Redis が正しく構成されていることを確認します。
* 重大な変更や移行に関する注意事項は、変更ログで確認してください。
* リリースを追いかけるために、公開されたら DockFlare Agent リポジトリをウォッチしてください。

楽しいトンネリングを！ 🚇
