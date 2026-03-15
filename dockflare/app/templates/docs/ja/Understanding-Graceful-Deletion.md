# Graceful Deletion を理解する

DockFlare が管理しているコンテナを停止しても、対応する公開ホスト名がすぐにオフラインにならないことがあります。これは **Graceful Deletion** という機能によるものです。

## Graceful Deletion とは

DockFlare は、コンテナ停止の瞬間に Cloudflare の入口ルールや DNS レコードを即削除するのではなく、ルールを **「pending_deletion」** としてマークし、タイマーを開始します。

関連する Cloudflare リソース（入口ルールと DNS レコード）は、このタイマー（**grace period / 猶予期間**）が期限切れになった時点で初めて完全に削除されます。

## なぜこれが役立つのでしょうか?

この機能は、一般的な運用シナリオにおけるサービスの中断を防ぐように設計されています。

* **コンテナの更新:** コンテナ イメージ (`docker compose up -d`) を更新すると、通常、Docker は古いコンテナを停止し、新しいコンテナを起動します。猶予期間がないと、サービスは短期間アクセスできなくなります。Graceful Deletion では、DNS レコードと入口ルールはアクティブなままで、DockFlare はそれらを新しいコンテナに再関連付けするだけなので、ダウンタイムを抑えられます。
* **一時的な再起動:** 設定を変更するためにコンテナを一時停止してから再起動する必要がある場合、猶予期間により、公開設定がそのまま維持されることが保証されます。

## `GRACE_PERIOD_SECONDS` 変数

猶予期間の長さは、`docker-compose.yml` で設定できる `GRACE_PERIOD_SECONDS` 環境変数で制御されます。

* デフォルト値は `600` 秒 (10 分) です。
* ニーズに合わせてこの値を調整できます。短くするとクリーンアップが速くなり、長くするとコンテナを再起動できる猶予が増えます。

**例:**
```yaml
services:
  dockflare:
    image: alplat/dockflare:stable
    # ... other settings
    environment:
      - GRACE_PERIOD_SECONDS=3600 # Set a 1-hour retention window
```

## 実際にどのように機能するか

1. **コンテナが停止しました:** `docker stop my-app` を実行します。
2. **削除保留中:** DockFlare が停止イベントを検出します。管理画面では、`my-app.example.com` のルールのステータスが **「pending_deletion」** として表示され、削除予定時刻が表示されます。
3. **2 つのシナリオ:**
    * **シナリオ A: 猶予期間の期限切れ:** コンテナが停止したままで猶予期間（10 分など）が期限切れになると、DockFlare のバックグラウンド クリーンアップ タスクが実行されます。Cloudflare Tunnel から入口ルールが削除され、CNAME DNS レコードが削除されます。
    * **シナリオ B: コンテナの再起動:** 猶予期間が期限切れになる前にコンテナを再起動すると（`docker start my-app`）、DockFlare は開始イベントを検出します。ルールが `pending_deletion` であることを確認し、削除をキャンセルしてステータスを **「active」** に戻します。サービスはそのまま継続して動作します。
