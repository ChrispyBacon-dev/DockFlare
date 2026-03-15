# DNS ゾーンの管理

DockFlare は、同じ Cloudflare アカウント内にある複数ドメイン（Cloudflare Zones）にまたがって DNS レコードを管理できます。つまり、1 つの DockFlare インスタンスから `service-a.domain-one.com` と `service-b.another-domain.org` の両方を運用できます。

## デフォルトゾーン

DockFlare の初期セットアップ時に **Zone ID** を指定します。これが DockFlare が DNS レコードを作成する **デフォルトゾーン** です。単一ドメインしか使わない場合は、基本的にこれだけで十分です。

## ラベルでゾーンを上書きする

デフォルト以外のドメインでサービスを公開したい場合は、`dockflare.zonename` ラベルを使います。

このラベルを付けると、そのサービスの DNS レコードを指定した Cloudflare Zone に作成するよう DockFlare に指示できます。

### 前提条件

この機能を使うには、利用中の **Cloudflare API Token** に対して、管理対象の **すべてのゾーン**について `Zone:DNS:Edit` 権限が必要です。

### 例

たとえば、デフォルトゾーンが `example.com` で、さらに `media.io` でもサービスを公開したいとします。

```yaml
services:
  # This service will be created in the default zone (example.com)
  service-one:
    image: nginx
    labels:
      - "dockflare.enable=true"
      - "dockflare.hostname=nginx.example.com"
      - "dockflare.service=http://service-one:80"

  # This service will be created in the 'media.io' zone
  service-two:
    image: portainer/portainer-ce
    labels:
      - "dockflare.enable=true"
      - "dockflare.hostname=portainer.media.io"
      - "dockflare.service=http://service-two:9000"
      # Override the default zone for this service
      - "dockflare.zonename=media.io"
```

この設定をデプロイすると、DockFlare は次の処理を行います。
1. `example.com` ゾーンに `nginx.example.com` の CNAME レコードを作成します。
2. `media.io` ゾーンに `portainer.media.io` の CNAME レコードを作成します。

両方のホスト名は、同じ Cloudflare Tunnel の入口ルールとして追加されます。

## 管理画面で DNS レコードを表示する

DockFlare 管理画面の **設定** ページでは、アカウント内の Cloudflare Tunnel 一覧と、それらを指している DNS レコードを確認できます。

複数ゾーンにまたがって DNS レコードを確実に検出したい場合は、`TUNNEL_DNS_SCAN_ZONE_NAMES` 環境変数を使います。

### `TUNNEL_DNS_SCAN_ZONE_NAMES`

この環境変数には、管理画面が DNS レコード検索時にスキャンするゾーン名をカンマ区切りで指定します。

**例 `docker-compose.yml`:**
```yaml
services:
  dockflare:
    image: alplat/dockflare:stable
    # ... other settings
    environment:
      # Tell the management UI to scan these zones in addition to the default one
      - TUNNEL_DNS_SCAN_ZONE_NAMES=media.io,another-domain.org
```

これにより、管理画面の DNS レコードビューアで、トンネルを指しているすべてのドメインを横断して確認できるようになります。
