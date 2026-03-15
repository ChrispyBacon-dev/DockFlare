# DockFlare Agent とマルチサーバーアーキテクチャ

DockFlare 3.0 では、複数の Docker ホストにまたがって Cloudflare Tunnel を管理できる分散実行モデルが導入されています。DockFlare **Master** が構成を調整し、軽量な **Agent** がワークロードのそばで動作して各ホストの `cloudflared` を Master と同期します。

このガイドでは、Agent をデプロイするためのアーキテクチャ、セキュリティモデル、段階的なワークフローについて説明します。

---

## なぜ Agent なのか？

* **compute と ingress の分離** – 単一の control plane を維持しつつ、ワークロードをユーザーの近くに配置できます。
* **ホスト単位の可視性** – Agent ごとの heartbeat、トンネル状態、コマンド履歴を監視できます。
* **最小権限のトークン** – 侵害された Agent だけを失効させ、Master や他ホストへの影響を最小化します。
* **堅牢な更新** – Master が一時的に利用できなくても、Agent は最後の既知構成でトラフィックを処理し続けます。

---

## コンポーネントの概要

| コンポーネント | 役割 |
|-----------|----------------|
| **Master (DockFlare)** | Web UI をホストし、状態を保存し、必要な ingress ルールを調整し、コマンドを発行します。 |
| **Redis** | キャッシュ、Agent の heartbeat、キューに入れられたコマンドを扱う backplane です。 |
| **DockFlare Agent** | ローカルの Docker イベントを監視し、コマンドを実行し、`cloudflared` を動かすヘッドレスコンテナです。 |
| **cloudflared** | Agent ごとに Cloudflare への実際のトンネル接続を処理します。 |

通常、Master と Redis は同じ場所で動作し、Agent はワークロードの近く（場合によってはリモートネットワーク上）で動作します。

---

## 前提条件

* Redis を構成した DockFlare Master ≥ v3.0（`REDIS_URL` が設定されていること）。必要に応じて `REDIS_DB_INDEX` を指定し、同じ Redis インスタンスを使う他コンテナからデータを分離します。
* Tunnel + Access 権限を持つ Cloudflare API トークン（以前のバージョンと同様）。
* 管理する予定のすべてのホスト上の Docker ランタイム。
* （オプション）Master を公開しない場合は、Master と Agent 間の専用ネットワークセグメントまたは VPN。

---

## ワークフローの概要

1. DockFlare UI（`Agents → Generate Key`）で **Agent API key** を生成します。
2. リモートホストに **DockFlare Agent** コンテナをデプロイし、Master URL とキーを渡します。
3. Agent が Master に **登録**され、ステータスが *Pending* として表示されます。
4. Master UI で Agent を **承認（enrol）** し、そのホストに Cloudflare Tunnel を割り当てるか作成します。
5. Master はコマンドをキューに入れます。Agent は **ポーリング** して設定を適用し、ステータスと heartbeat を報告します。DockFlare はホスト名ごとに対象ゾーンを自動検出します（検出に失敗した場合のみデフォルトゾーンにフォールバックします）。
6. Agent ホスト上でコンテナが起動/停止すると、Agent がイベントを Master にストリーミングし、DNS、Access ポリシー、Tunnel の ingress ルールを更新します。

---

## DockFlare Agent のデプロイ

> ℹ️ Agent は `alplat/dockflare-agent` として公開されます。パブリックリポジトリが公開されるまでは、DockFlare 3.0 に含まれる `DockFlare-agent` ソースツリーからビルドできます。

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

- `docker network create cloudflare-net` を 1 回実行して、Master と Agent が使う共有ネットワークを作成します。
- socket proxy は、Agent が到達できる Docker API の範囲を制限します。`1` に設定した機能だけが公開されます。
- Agent イメージは特権のない `dockflare` ユーザー（UID/GID 65532）として実行されます。`/app/data` などのマウント先がそのアカウントで書き込み可能であることを確認するか、ホストに合わせるために `DOCKFLARE_UID/DOCKFLARE_GID` を使って再ビルドしてください。
- `.env` に `DOCKFLARE_MASTER_URL` と `DOCKFLARE_API_KEY` を設定します。`LOG_LEVEL` や `DOCKER_HOST` などの上書きも同じ方法で指定できます。

---

## セキュリティモデル

* **Master API キー** – 管理 API を保護します。UI では `Show Master API Key` をクリックした後にのみ表示されます。
* **Agent API キー** – Agent ごとに一意です。キーを取り消すと、そのホストからの以後の登録/コマンドが即座にブロックされます。
* **Redis** – キューとキャッシュに使用されます。信頼できる LAN の外部で実行している場合は、セキュリティで保護します (パスワード + ネットワーク ACL)。
* **トランスポート** – Agent のトラフィックが暗号化されるように、HTTPS の背後で Master を実行します (例: Cloudflare Access 経由)。
* **最小特権ランタイム** – Agent コンテナは `dockflare` ユーザー (UID/GID 65532) として実行され、socket proxy によって Docker アクセスの範囲をコンテナ検査とライフサイクル制御に限定します。

### 推奨されるハードニング

1. Agent キーを vault/パスワードマネージャーに保管し、定期的にローテーションします。
2. **パスワードログインを無効にしないでください** - 代わりに OAuth/OIDC で SSO を有効にしてください。どうしても無効にする場合は、同一 Docker ネットワーク上のコンテナが外部認証を迂回できるリスクがある点を理解してください。詳細は [Web UI へのアクセス - パスワードログインの無効化](Accessing-the-Web-UI.md) を参照してください。
3. 権限の分離を強めるには、Agent ごとに個別のトンネルを使用します。
4. `Agents` ページで heartbeat の欠落を監視します。オフラインノードは UI から直接削除できます。

---

## トラブルシューティング

| 症状 | 対処 |
|---------|------|
| status が `pending` のまま | 正しい API キーで登録されていることを確認し、UI から enrol します。 |
| コマンドが消化されない | Redis 接続と、Agent コンテナのクロック同期を確認します。 |
| DNS が更新されない | Master が Cloudflare に到達でき、Agent がコンテナイベントを送信できている必要があります。`docker logs dockflare-agent` を確認してください。 |
| heartbeat が offline | Agent と Master 間のネットワークパスを確認します。一般的な原因はファイアウォール、または TLS の問題です。 |

---

## 次のステップ

* リポジトリの README で更新されたクイック スタートを確認して、Redis が構成されていることを確認します。
* 重大な変更と移行に関する注意事項については、変更ログを確認してください。
* リリースを最新の状態に保つために、公開されたら DockFlare Agent リポジトリをサブスクライブします。

楽しいトンネリングを！ 🚇
