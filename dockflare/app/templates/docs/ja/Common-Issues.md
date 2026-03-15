# 一般的な問題

このページでは、よくある問題とその対処方法をまとめています。

---

### 問題: DockFlare コンテナが起動に失敗する、または再起動ループに入る

**解決策:**
1. **Docker ログを確認する:** まずは DockFlare コンテナのログを確認してください。次のコマンドを実行します。
    ```bash
    docker logs dockflare
    ```
2. **エラー内容を確認する:** よくある原因は次のとおりです。
    * `docker-compose.yml` の記述ミス（構文エラー、ボリュームマウントの問題など）
    * Docker デーモン自体の問題
    * `docker-socket-proxy` サービスや `DOCKER_HOST` 設定に関する接続・権限の問題

---

### 問題: Cloudflare に DNS レコードが作成されない

**解決策:**
1. **DockFlare のログを確認する:** Cloudflare API に関連するエラーメッセージを探してください。多くの場合、ログに API 呼び出しが失敗した理由がそのまま表示されます。
2. **API トークンの権限を確認する:** これが最もよくある原因です。Cloudflare API トークンに必要な権限があることを確認してください。最低限必要なのは次のとおりです。
    * DockFlare で管理するすべてのゾーンに対する `Zone:DNS:Edit`
    * `Zone:Zone:Read`
3. **ゾーン設定を確認する:**
    * セットアップ時に入力した **Zone ID** が正しいか確認してください。
    * `dockflare.zonename` ラベルを使っている場合は、ゾーン名のスペルが正しいか再確認してください。

---

### 問題: Access Policy（Zero Trust）がサービスに適用されない

**解決策:**
1. **API トークンの権限を確認する:** API トークンに `Account:Access: Apps and Policies:Edit` 権限があることを確認してください。
2. **管理画面のオーバーライドを確認する:** DockFlare ダッシュボードで、そのルールに `UI Override` ステータスが付いていないか確認してください。この状態では、管理画面側の設定がラベルより優先されます。
3. **Access Group ID を確認する:** `dockflare.access.group` を使っている場合は、ラベルに指定した ID が **完全一致** で Access Policies ページの Access Group ID と一致している必要があります。
4. **Cloudflare ダッシュボードを確認する:** Cloudflare Zero Trust ダッシュボードで **Access -> Applications** を開き、Access Application が作成されているか確認してください。API レスポンスには出てこないエラーが Cloudflare 側に表示されることがあります。

---

### 問題: サービスにアクセスすると `ERR_TOO_MANY_REDIRECTS` が発生する

**解決策:**
このエラーは、ほとんどの場合、オリジンサービスと Cloudflare 間の SSL/TLS 設定ミスが原因です。

1. **Cloudflare の SSL/TLS モードを確認する:** Cloudflare ダッシュボードで対象ドメインの SSL/TLS 設定を開き、暗号化モードが **Full (Strict)** になっていることを確認してください。
2. **二重リダイレクトを避ける:** バックエンドアプリケーションも HTTP から HTTPS にリダイレクトしている場合、Cloudflare の `Flexible` SSL モードでループが発生することがあります。
3. **サービス URL で `https` を使う:** バックエンドサービスが HTTPS をサポートしている場合は、`dockflare.service` ラベルに `https://` を使ってください（例: `dockflare.service=https://my-app:443`）。これにより `cloudflared` からサービスへの通信も暗号化されます。

---

### 問題: Traefik/Proxmox 配下のサービスが Cloudflare の `Match SNI to Host` を有効にしたときだけ動作する

**解決策:**
1. DockFlare で手動ルールを編集し、**Match SNI to Host** を有効にします。
2. ルールを保存し、Cloudflare Zero Trust でルートを確認します。
3. DockFlare が管理していない Cloudflare 側の route フィールドも保持したい場合は、**設定 → 一般設定** で **Preserve Unmanaged Cloudflare Ingress Fields** を有効にします。

---

### 問題: 管理対象の `cloudflared-agent` コンテナが "stale network" エラーで起動しない

**解決策:**
これは、Agent が使用していた Docker ネットワークが削除・再作成された場合に発生することがあります。DockFlare はこのケースを自動処理するように設計されています。

1. **DockFlare を再起動する:** DockFlare コンテナを `docker compose restart dockflare` で再起動すれば、通常は解消します。
2. **内部動作:** 起動時に DockFlare は管理対象 Agent の状態を確認します。この問題を検出すると、壊れた Agent コンテナを自動的に削除し、正しい設定で新しい Agent コンテナを作成します。これは `v1.9.5` で修正された不具合に関連するため、DockFlare を新しいバージョンにしておくことも重要です。
