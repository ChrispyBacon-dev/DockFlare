# 先决条件  

在开始之前，请确保您具备以下条件：  

* **Docker 和 Docker Compose：** DockFlare 是一个基于 Docker 的应用程序，因此您需要在系统上安装 Docker 和 Docker Compose。
* **Cloudflare 帐户：** 您需要一个 Cloudflare 帐户来管理您的域并创建 API 令牌。
* **您的 Cloudflare 帐户 ID：** 您可以在 Cloudflare 仪表板中找到您的帐户 ID。
* **您要使用的域的区域 ID：** Cloudflare 中的每个域都有一个唯一的区域 ID。
* **Cloudflare API 令牌：** 您需要创建具有以下权限的 Cloudflare API 令牌：
    * `Account:Cloudflare Tunnel:Write`
    * `Account:Account Settings:Read`
    * `Account:Access: Apps and Policies:Write`
    * `Account:Access: Organizations, Identity Providers, and Groups:Write`
    * `Account:Access: Service Tokens:Write`
    * `Zone:Zone:Read`
    * `Zone:DNS:Write`

    **For optional DockFlare Email features, add these additional permissions:**
    * `Workers Scripts:Write`
    * `Workers KV Storage:Write`
    * `Workers R2 Storage:Write`
    * `Email Routing Addresses:Write`
    * `Email Routing Rules:Write`

![Cloudflare API 权限](../static/images/cf.png)