# 状態の永続化

DockFlare はステートフルなアプリケーションです。管理しているサービス、管理画面のオーバーライド、そのほかの設定情報を保持しておく必要があります。この状態はディスクに保存されるため、DockFlare コンテナを再起動したり作り直したりしても設定が失われません。

## 状態の保存方法

DockFlare は、コンテナ内の `/app/data` ディレクトリにある 3 つの重要なファイルに状態を保存します。

1. `dockflare_config.dat`: 最も重要なファイルです。主要な設定と機密情報が **暗号化** された形式で保存されます。内容には次のものが含まれます。
    * Cloudflare API トークンとアカウント ID
    * DockFlare 管理画面のパスワードハッシュ
    * 管理画面で設定したトンネル名やゾーン ID などの主要設定

2. `agent_keys.dat`: すべての Agent API キーと、そのメタデータ（所有者、状態、タイムスタンプ）を含む暗号化ストアです。このファイルを安全に保管することで、古いキーの再利用を防げます。

3. `state.json`: 管理対象サービスの動的な状態を、プレーンな JSON 形式で保存するファイルです。内容には次のものが含まれます。
    * Docker ラベル由来か管理画面で手動作成したものかを問わず、DockFlare が管理しているすべての入口ルール
    * Access Policy に適用された管理画面オーバーライド
    * 作成したすべての Access Groups
    * 停止済みだが猶予期間内にあるサービスの `pending_deletion` 状態

## 永続ボリュームの重要性

すべての設定は `/app/data` ディレクトリに保存されるため、このディレクトリをホスト側の永続ボリュームにマッピングすることが**非常に重要**です。

永続ボリュームを使わない場合、DockFlare コンテナを削除して再作成するたびに（たとえばイメージ更新時など）、**設定、管理画面のパスワード、ルール構成がすべて失われます**。

### 推奨される Docker Compose 設定

推奨される `docker-compose.yml` では、名前付きボリュームを定義して `/app/data` にマウントすることで、これを自動的に処理します。

```yaml
services:
  dockflare:
    # ... other settings
    volumes:
      # This line ensures your data is persisted
      - ./dockflare_data:/app/data

volumes:
  # This defines the named volume on your host
  dockflare_data:
```

この設定では、`dockflare_config.dat`、`agent_keys.dat`、`state.json` がホスト上の `dockflare_data` ディレクトリに保存されるため、コンテナ更新後も設定を安全に維持できます。

## バックアップと復元

DockFlare では、重要なデータを 1 つの暗号化バックアップアーカイブにまとめて保存できるようになりました。Redis キャッシュは、プライベートな `dockflare-internal` ネットワーク上で安全に再構築できるため、バックアップには含まれません。**設定 → バックアップと復元** では、次を含む `.zip` をダウンロードできます。

* `dockflare_config.dat`
* `dockflare.key`
* `agent_keys.dat`
* `state.json`（存在する場合）
* 整合性検証用のチェックサムを含むマニフェスト

アーカイブを復元すると、これらのファイルが再作成され、実行中のインスタンスに再読み込みされます。従来どおり `state.json` 単体のアップロードも受け付けていますが、復元されるのはルールのメタデータだけで、認証情報はあとで手動入力が必要です。
完全なアーカイブを復元した場合、DockFlare はコンテナを自動的に再起動し、暗号化された設定をすぐに読み込みます。
