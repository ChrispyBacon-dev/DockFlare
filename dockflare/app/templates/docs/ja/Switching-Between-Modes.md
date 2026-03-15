# モード間の切り替え

DockFlare は、**Internal**（デフォルト）と **External** `cloudflared` モードをいつでも切り替えられます。このガイドでは、移行をスムーズに行うための手順を説明します。

2 つのモードの詳細な比較については、[内部 vs. 外部 `cloudflared`](Internal-vs-External-cloudflared.md) ページを参照してください。

---

## 内部モードから外部モードへの切り替え

この手順では、自分で `cloudflared` エージェントを用意し、DockFlare にそれを使うよう指定します。

**ステップ 1: 外部 `cloudflared` エージェントをセットアップする**

まず、自分で `cloudflared` エージェントをセットアップして起動します。ホスト OS 上のプロセスでも、別の Docker コンテナでも構いません。

* 特定の Cloudflare トンネルを使用するように設定されていることを確認してください。
* **Tunnel ID**（UUID）を控えます。
* エージェントを起動し、正しく実行されていて、Cloudflare ダッシュボードに「接続済み」と表示されていることを確認します。

**ステップ 2: DockFlare を再構成して再起動します**

次に、DockFlare コンテナの環境変数を更新して External mode に切り替えます。

`docker-compose.yml` 内:
```yaml
services:
  dockflare:
    image: alplat/dockflare:stable
    # ... other settings
    environment:
      # Enable external mode
      - USE_EXTERNAL_CLOUDFLARED=true
      # Provide the ID of your running tunnel
      - EXTERNAL_TUNNEL_ID=your-tunnel-uuid-goes-here
```

**ステップ 3: 変更をデプロイする**

`docker compose up -d` を実行して、環境変数を反映した DockFlare コンテナを再作成します。

更新後の DockFlare コンテナ起動時に、次が行われます。
1. `USE_EXTERNAL_CLOUDFLARED` が `true` であることが検出されます。
2. 管理対象の `cloudflared-agent` コンテナを **停止して削除**します。
3. `EXTERNAL_TUNNEL_ID` で指定したトンネルへ、すべての入口ルール設定を送るようになります。

これで、サービスは外部管理の `cloudflared` エージェントによって提供されるようになります。

---

## 外部モードから内部モードへの切り替え

こちらは DockFlare に制御を戻すだけなので、より簡単です。

**ステップ 1: DockFlare を再構成する**

DockFlare の `docker-compose.yml` から External mode の環境変数を削除します。

```yaml
services:
  dockflare:
    image: alplat/dockflare:stable
    # ... other settings
    environment:
      # Remove the following two lines
      # - USE_EXTERNAL_CLOUDFLARED=true
      # - EXTERNAL_TUNNEL_ID=your-tunnel-uuid-goes-here
```

**ステップ 2: 変更をデプロイする**

`docker compose up -d` を実行して DockFlare コンテナを再作成します。

更新後の DockFlare コンテナ起動時に、次が行われます。
1. `USE_EXTERNAL_CLOUDFLARED` が `false` であることが検出されます。
2. 内部 `cloudflared-agent` コンテナを自動的に **作成、構成、開始**します。
3. この新しいエージェントは、DockFlare 設定で定義されたトンネル名を使うように構成されます。

**ステップ 3: 外部エージェントを廃止する**

新しい内部エージェントが正しく動作してトラフィックを処理していることを確認したら、外部で動かしていた `cloudflared` エージェントは安全に停止・削除できます。
