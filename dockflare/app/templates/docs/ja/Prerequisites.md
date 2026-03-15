# 前提条件

作業を始める前に、次のものを用意してください。

* **Docker と Docker Compose:** DockFlare は Docker ベースのアプリケーションなので、両方がシステムにインストールされている必要があります。
* **Cloudflare アカウント:** ドメインの管理や API トークンの作成に必要です。
* **Cloudflare Account ID:** Cloudflare ダッシュボードで確認できます。
* **利用するドメインの Zone ID:** Cloudflare 上の各ドメインには固有の Zone ID があります。
* **Cloudflare API Token:** 次の権限を持つ Cloudflare API トークンを作成する必要があります。
    * `Account:Cloudflare Tunnel:Edit`
    * `Account:Account Settings:Read`
    * `Account:Access: Apps and Policies:Edit`
    * `Account:Access: Organizations, Identity Providers, and Groups:Edit`
    * `Zone:Zone:Read`
    * `Zone:DNS:Edit`

![Cloudflare API 権限](../static/images/cf.png)
