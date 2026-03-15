# Prometheus と Grafana によるモニタリング

DockFlare が管理する `cloudflared` Agent は、さまざまなパフォーマンス/ヘルス指標を Prometheus 形式で公開できます。これらを収集して可視化することで、トンネルのトラフィック、遅延、エラー率などを把握できます。

このガイドでは、メトリクスエンドポイントの有効化と、Prometheus + Grafana の監視スタックを簡単に用意する方法を説明します。

## ステップ 1: DockFlare でメトリクス エンドポイントを有効にする

最初に、管理対象 `cloudflared` Agent で Prometheus のメトリクスエンドポイントを有効にするよう DockFlare に指示します。

DockFlare コンテナの `CLOUDFLARED_METRICS_PORT` 環境変数を設定します。

**例 `docker-compose.yml`:**
```yaml
services:
  dockflare:
    image: alplat/dockflare:stable
    # ... other settings
    environment:
      # Enable the metrics endpoint on port 2000 inside the container
      - CLOUDFLARED_METRICS_PORT=2000
```
この変数を使用して DockFlare を再起動すると、指定されたポートで有効になっているメトリクス サーバーを使用して、管理対象の `cloudflared` エージェントが自動的に再作成されます。

**注:** この機能はデフォルトの **Internal mode** でのみ利用できます。[External mode](External-cloudflared-Mode.md) の場合、メトリクスエンドポイントの有効化は自分で管理している `cloudflared` 側で行ってください。

## ステップ 2: 監視スタックをセットアップする

監視スタックがない場合でも、Docker Compose で手早くセットアップできます。DockFlare リポジトリの `/examples` にサンプル構成があります。

Prometheus と Grafana をセットアップして DockFlare を監視する方法に関する完全なコピー＆ペースト ガイドについては、リポジトリ内の **[`grafana quick setup.md`](https://github.com/ChrispyBacon-dev/DockFlare/blob/main/examples/grafana%20quick%20setup.md)** ファイルを参照してください。

このガイドでは次を扱います。
1. 必要なディレクトリ構造を作成します。
2. Prometheus サービスと Grafana サービスを `docker-compose.yml` に追加します。
3. `cloudflared` エージェントからメトリクスを収集するように Prometheus を構成します。
4. Prometheus データ ソースを使用して Grafana を自動的にプロビジョニングします。

## ステップ 3: 事前に作成された Grafana ダッシュボードをインポートする

可視化を簡単にするため、DockFlare は `cloudflared` Agent が公開するメトリクスに対応した Grafana ダッシュボードを用意しています。

1. ダッシュボードは、リポジトリの `/examples` ディレクトリで **[`dashboard.json`](https://github.com/ChrispyBacon-dev/DockFlare/blob/main/examples/dashboard.json)** として利用できます。
2. このファイルをダウンロードします。
3. Grafana インスタンスにログインします。
4. [ダッシュボード] セクションに移動し、[インポート] をクリックします。
5. `dashboard.json` ファイルをアップロードします。
6. Prometheus データ ソースを選択し、ダッシュボードをインポートします。

リクエスト数、エラー率、接続レイテンシーなど、Cloudflare Tunnel のパフォーマンス概要を確認できるようになります。

![Grafana ダッシュボードの例](../static/images/grafana_dashboard_example.png)
