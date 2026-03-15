# ヘルスチェック

DockFlare には、Docker の組み込みヘルスチェック機能で使える専用エンドポイントがあります。これにより、Docker は DockFlare アプリケーションの状態を監視し、応答しなくなった場合に自動で再起動できます。

## `/ping` エンドポイント

DockFlare は `/ping` にシンプルな HTTP エンドポイントを公開します。

* **目的:** DockFlare の Web サーバーが起動していて、正常に応答しているかを自動システムが確認できるようにするためのものです。
* **認証:** このエンドポイントは **認証不要** です。ログインしていなくてもアクセスできるため、Docker の内部ヘルスチェックで利用できます。
* **正常時の応答:** 正常に動作している DockFlare は、`/ping` へのリクエストに **HTTP 200 OK** で応答します。
* **バージョン情報:** `/ping` のレスポンス本文には、実行中の DockFlare のバージョンも含まれます。

## Docker Compose でヘルスチェックを設定する方法

`docker-compose.yml` の `dockflare` サービスに `healthcheck` セクションを追加すると、Docker がアプリケーションの状態を自動監視できます。

```yaml
services:
  dockflare:
    image: alplat/dockflare:stable
    container_name: dockflare
    restart: unless-stopped
    # ... other settings
    healthcheck:
      # The command to run to check health.
      # curl is used to make an HTTP request to the ping endpoint.
      test: ["CMD", "curl", "-f", "http://localhost:5000/ping"]
      # How often to run the check
      interval: 1m30s
      # How long to wait for a response
      timeout: 10s
      # How many consecutive failures before marking as unhealthy
      retries: 3
      # How long to wait after the container starts before running the first check
      start_period: 40s
```

### `healthcheck` 設定の内訳

* `test`: Docker がコンテナ内で実行するコマンドです。`curl -f` は `/ping` に HTTP リクエストを送り、応答が HTTP 200 OK でなければゼロ以外の終了コードを返します。
* `interval`: Docker は 90 秒ごとにこのチェックを実行します。
* `timeout`: コマンド完了まで最大 10 秒待機します。
* `retries`: チェックが 3 回連続で失敗すると、Docker はコンテナを `unhealthy` と判定します。
* `start_period`: コンテナ起動後、最初のヘルスチェック実行まで 40 秒待機します。これにより、アプリケーションの初期化時間を確保できます。

この設定を適用すると、`docker ps` を実行してコンテナの状態を確認できます。ヘルスチェックに合格していれば、ステータス欄に `(healthy)` と表示されます。コンテナが異常になった場合、Docker は `restart` ポリシー（例: `unless-stopped`）に基づいて自動的に再起動します。
