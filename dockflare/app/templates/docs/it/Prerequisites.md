# Prerequisiti  

Prima di iniziare, assicurati di avere quanto segue:  

* **Docker e Docker Compose:** DockFlare è un'applicazione basata su Docker, quindi avrai bisogno che sia Docker che Docker Compose siano installati sul tuo sistema.
* **Un account Cloudflare:** avrai bisogno di un account Cloudflare per gestire i tuoi domini e creare token API.
* **Il tuo ID account Cloudflare:** Puoi trovare il tuo ID account nella dashboard di Cloudflare.
* **L'ID di zona per il dominio che desideri utilizzare:** Ogni dominio in Cloudflare ha un ID di zona univoco.
* **Un token API Cloudflare:** Dovrai creare un token API Cloudflare con le seguenti autorizzazioni:
    * `Account:Cloudflare Tunnel:Edit`
    * `Account:Account Settings:Read`
    * `Account:Access: Apps and Policies:Edit`
    * `Account:Access: Organizations, Identity Providers, and Groups:Edit`
    * `Zone:Zone:Read`
    * `Zone:DNS:Edit`  

![Autorizzazioni API Cloudflare](../static/images/cf.png)