# デバッグとログ

DockFlare の問題を調査するときに最も重要なのは、DockFlare コンテナ本体と管理対象 `cloudflared` Agent が出力するログです。

## 1. DockFlare コンテナログの確認

最も重要な情報源は、DockFlare コンテナ自身が出力するログです。ここを見ると、DockFlare が今何をしているかをリアルタイムで詳しく把握できます。

### ログで確認できる内容
* Docker コンテナの起動・停止イベントの検出
* `dockflare.*` ラベルの処理内容
* Cloudflare API への呼び出し
* Cloudflare API から返された成功メッセージや詳細なエラー
* リソースクリーンアップなどのバックグラウンドタスクの状態

### ログの確認方法
ログを確認するには、ターミナルで次の Docker コマンドを実行します。
```bash
# View the full log history
docker logs dockflare

# Follow the logs in real-time
docker logs -f dockflare
```

## 2. 管理画面のリアルタイムログを使う

DockFlare ダッシュボードのメインページ下部には、**リアルタイムログビューア** が用意されています。

ここには `docker logs -f dockflare` と同じ内容がストリーミング表示されるため、ブラウザを離れずに現在の動作状況を確認できます。特に、コンテナを起動・停止した直後に DockFlare がどのような処理をしているかを確認したいときに便利です。

## 3. `cloudflared` Agent ログの確認

サーバーと Cloudflare ネットワーク間の接続に問題があると思われる場合は、`cloudflared` Agent コンテナのログを直接確認してください。

### Agent ログの確認方法
まず Agent コンテナ名を確認します。デフォルトでは `cloudflared-agent-<tunnel-name>` という名前になります。`<tunnel-name>` は DockFlare 設定で指定したトンネル名です。

正確な名前は `docker ps` で確認できます。

名前を取得したら、次を実行します。
```bash
# Replace with the actual container name
docker logs cloudflared-agent-dockflare-tunnel
```

これらのログは、次のような問題の切り分けに役立ちます。
* Cloudflare edge への接続エラー
* トンネルトークンの認証エラー
* プロキシされるトラフィックのプロトコルレベルのエラー

**注:** これはデフォルトの **Internal Mode** を使っている場合に限ります。[External Mode](External-cloudflared-Mode.md) を使っている場合は、自分で管理している `cloudflared` プロセスのログを確認してください。

## 4. Cloudflare ダッシュボードの確認

最後に、Cloudflare ダッシュボード自体も重要なデバッグ手段です。
* **DNS ページ:** CNAME レコードが想定どおりに作成されているか確認します。
* **Zero Trust Dashboard:** **Access -> Tunnels** でトンネルの状態と入口ルールを確認します。
* **Zero Trust Dashboard:** **Access -> Applications** で Zero Trust ポリシーの設定や状態を確認します。ポリシーの "Last Seen" は有用な手がかりになることがあります。
