# ワイルドカード ドメインの使用

DockFlare は、ワイルドカードドメイン（例: `*.example.com`）を使って複数サブドメインのトラフィックを 1 つのサービスへルーティングできます。マルチテナントサービスや、Heimdall のように動的なサブドメインを扱うアプリで特に便利です。

## 仕組み

ワイルドカードホスト名を使うと、より具体的な DNS レコードを持たないサブドメインのトラフィックが、Cloudflare Tunnel によって指定サービスへルーティングされます。

たとえば、`*.apps.example.com` を構成すると、`service1.apps.example.com`、`service2.apps.example.com` などのトラフィックはすべて同じ宛先コンテナにルーティングされます。

## 重要な考慮事項

通常のホスト名と違い、DockFlare は **ワイルドカードドメインの DNS レコードを自動作成できません**。Cloudflare ダッシュボードでワイルドカード DNS レコードを手動作成する必要があります。

DockFlare は引き続き Cloudflare Tunnel 内の **入口ルール** を管理しますが、最初の DNS セットアップだけは手動です。

## ステップバイステップガイド

ここでは `*.plex.example.com` を例に、DockFlare でワイルドカードドメインを設定する手順を説明します。

### ステップ 1: ワイルドカード DNS レコードを手動で作成する

1. **Cloudflare ダッシュボード**にログインします。
2. ドメインの DNS 設定に移動します。
3. **レコードの追加** をクリックし、次の内容で CNAME レコードを作成します。
    * **タイプ:** `CNAME`
    * **名前:** `*.plex`（メインドメインが `plex.example.com` の場合は `*` でも可）
    * **ターゲット:** トンネルのパブリックホスト名。Cloudflare Zero Trust ダッシュボードの **Access -> Tunnels** にあります。`your-tunnel-uuid.cfargotunnel.com` のような形式です。
    * **プロキシ ステータス:** **プロキシ済み** (オレンジ色の雲) であることを確認します。

    この手動 DNS レコードによって、`*.plex.example.com` のトラフィックがトンネルへ送られるようになります。

### ステップ 2: ワイルドカード ラベルを使用してサービスを構成する

次に `docker-compose.yml` で、ワイルドカードホスト名ラベルを使ってサービスを構成します。

```yaml
services:
  my-proxy-manager:
    image: nginxproxymanager/nginx-proxy-manager
    restart: unless-stopped
    networks:
      - cloudflare-net
    labels:
      - "dockflare.enable=true"
      # Use the wildcard hostname here
      - "dockflare.hostname=*.plex.example.com"
      - "dockflare.service=http://my-proxy-manager:81"
```

### ステップ 3: 導入と検証

1. `docker-compose.yml` ファイルを保存し、`docker compose up -d` を実行します。
2. DockFlare がコンテナを検出し、Cloudflare Tunnel 内に `*.plex.example.com` の入口ルールを作成します。
3. DockFlare 管理画面と Cloudflare ダッシュボードのトンネル設定で確認できます。

これで、`sonarr.plex.example.com` や `radarr.plex.example.com` などへのリクエストは Cloudflare Tunnel を経由して `my-proxy-manager` コンテナにルーティングされるようになります。
