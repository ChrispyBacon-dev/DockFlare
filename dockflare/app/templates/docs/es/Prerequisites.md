# Requisitos previos  

Antes de comenzar, asegúrese de tener lo siguiente:  

* **Docker y Docker Compose:** DockFlare es una aplicación basada en Docker, por lo que necesitarás tener instalados Docker y Docker Compose en tu sistema.
* **Una cuenta de Cloudflare:** Necesitará una cuenta de Cloudflare para administrar sus dominios y crear tokens API.
* **Su ID de cuenta de Cloudflare:** Puede encontrar su ID de cuenta en el panel de Cloudflare.
* **El ID de zona del dominio que deseas usar:** Cada dominio en Cloudflare tiene un ID de zona único.
* **Un token de API de Cloudflare:** Deberá crear un token de API de Cloudflare con los siguientes permisos:
    * `Account:Cloudflare Tunnel:Edit`
    * `Account:Account Settings:Read`
    * `Account:Access: Apps and Policies:Edit`
    * `Account:Access: Organizations, Identity Providers, and Groups:Edit`
    * `Zone:Zone:Read`
    * `Zone:DNS:Edit`  

![Permisos de la API de Cloudflare](../static/images/cf.png)