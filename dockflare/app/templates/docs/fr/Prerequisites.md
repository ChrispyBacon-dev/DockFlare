# Prérequis  

Avant de commencer, assurez-vous d'avoir les éléments suivants :  

* **Docker & Docker Compose :** DockFlare est une application basée sur Docker, vous aurez donc besoin d'installer Docker et Docker Compose sur votre système.
* **Un compte Cloudflare :** Vous aurez besoin d'un compte Cloudflare pour gérer vos domaines et créer des jetons API.
* **Votre identifiant de compte Cloudflare :** Vous pouvez trouver votre identifiant de compte dans le tableau de bord Cloudflare.
* **L'ID de zone du domaine que vous souhaitez utiliser :** Chaque domaine dans Cloudflare possède un ID de zone unique.
* **Un jeton API Cloudflare :** Vous devrez créer un jeton API Cloudflare avec les autorisations suivantes :
    * `Account:Cloudflare Tunnel:Edit`
    * `Account:Account Settings:Read`
    * `Account:Access: Apps and Policies:Edit`
    * `Account:Access: Organizations, Identity Providers, and Groups:Edit`
    * `Zone:Zone:Read`
    * `Zone:DNS:Edit`  

![Autorisations de l'API Cloudflare](../static/images/cf.png)