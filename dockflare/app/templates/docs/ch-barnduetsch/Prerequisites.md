# Was du bruuchsch

Bevor du losleisch, lueg, dass das da parat isch:

* **Docker u Docker Compose:** DockFlare lauft i Docker, drum mues das uf dim System iigrichtet si.
* **Es Cloudflare-Konto:** Das bruuchsch, zum Tunnel, DNS u Zero Trust z verwalte.
* **Dini Cloudflare Account ID:** Die findscht im Cloudflare-Dashboard.
* **D Zone ID vo dr Domain, wo du wotsch bruuche:** Jede Zone het ihri eigeti ID.
* **Es Cloudflare API-Token:** Erstell es Token mit dene Berechtige:
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

![Cloudflare API Berechtigungen](../static/images/cf.png)
