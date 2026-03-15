# Was du bruuchsch

Bevor du losleisch, lueg, dass das da parat isch:

* **Docker u Docker Compose:** DockFlare lauft i Docker, drum mues das uf dim System iigrichtet si.
* **Es Cloudflare-Konto:** Das bruuchsch, zum Tunnel, DNS u Zero Trust z verwalte.
* **Dini Cloudflare Account ID:** Die findscht im Cloudflare-Dashboard.
* **D Zone ID vo dr Domain, wo du wotsch bruuche:** Jede Zone het ihri eigeti ID.
* **Es Cloudflare API-Token:** Erstell es Token mit dene Berechtige:
  * `Account:Cloudflare Tunnel:Edit`
  * `Account:Account Settings:Read`
  * `Account:Access: Apps and Policies:Edit`
  * `Account:Access: Organizations, Identity Providers, and Groups:Edit`
  * `Zone:Zone:Read`
  * `Zone:DNS:Edit`

![Cloudflare API Berechtigungen](../static/images/cf.png)
