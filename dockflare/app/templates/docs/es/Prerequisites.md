# Requisitos previos  

Antes de comenzar, asegúrese de tener lo siguiente:  

* **Docker y Docker Compose:** DockFlare es una aplicación basada en Docker, por lo que necesitarás tener instalados Docker y Docker Compose en tu sistema.
* **Una cuenta de Cloudflare:** Necesitará una cuenta de Cloudflare para administrar sus dominios y crear tokens API.
* **Su ID de cuenta de Cloudflare:** Puede encontrar su ID de cuenta en el panel de Cloudflare.
* **El ID de zona del dominio que deseas usar:** Cada dominio en Cloudflare tiene un ID de zona único.
* **Un token de API de Cloudflare:** Deberá crear un token de API de Cloudflare con los siguientes permisos:
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

![Permisos de la API de Cloudflare](../static/images/cf.png)