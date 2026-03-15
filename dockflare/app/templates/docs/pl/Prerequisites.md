# Warunki wstępne  

Zanim zaczniesz, upewnij się, że masz następujące elementy:  

* **Docker i Docker Compose:** DockFlare to aplikacja oparta na Dockerze, dlatego w swoim systemie musisz mieć zainstalowane zarówno Docker, jak i Docker Compose.
* **Konto Cloudflare:** Będziesz potrzebować konta Cloudflare, aby zarządzać swoimi domenami i tworzyć tokeny API.
* **Identyfikator Twojego konta Cloudflare:** Identyfikator Twojego konta znajdziesz w panelu kontrolnym Cloudflare.
* **Identyfikator strefy dla domeny, której chcesz używać:** Każda domena w Cloudflare ma unikalny identyfikator strefy.
* **Token API Cloudflare:** Musisz utworzyć token API Cloudflare z następującymi uprawnieniami:
    * `Account:Cloudflare Tunnel:Edit`
    * `Account:Account Settings:Read`
    * `Account:Access: Apps and Policies:Edit`
    * `Account:Access: Organizations, Identity Providers, and Groups:Edit`
    * `Zone:Zone:Read`
    * `Zone:DNS:Edit`  

![Uprawnienia API Cloudflare](../static/images/cf.png)