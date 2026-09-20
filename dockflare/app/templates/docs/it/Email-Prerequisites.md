# Prerequisiti e configurazione della Suite e-mail

Prima di abilitare la Suite e-mail, assicurati che il tuo ambiente e il tuo account Cloudflare siano configurati correttamente.

## Requisiti Cloudflare

1.  **Gestione del dominio:** Il tuo dominio deve essere attivo su Cloudflare.
2.  **Email Routing (In entrata):** Cloudflare Email Routing è disponibile su tutti i piani, incluso quello gratuito. DockFlare configura automaticamente i record MX, SPF e DMARC necessari.
3.  **Email Sending (In uscita):** Cloudflare Email Sending è attualmente in Beta. DockFlare configura automaticamente i record di firma DKIM e il sottodominio di invio. Tuttavia, l'invio a indirizzi esterni richiede:
    - Un **Cloudflare Workers Paid Plan** (5 $/mese).
    - L'attivazione manuale di **CF Email Sending (Beta)** nella dashboard Cloudflare sotto **Email → Email Sending**.
    - Senza questi passaggi, l'invio in uscita è limitato agli indirizzi Cloudflare verificati.
4.  **Archiviazione R2:** R2 deve essere abilitato nella tua dashboard Cloudflare. R2 include un livello gratuito di 10 GB, ma potrebbe essere necessario aggiungere un metodo di pagamento per attivarlo.

## Autorizzazioni del token API

La Suite e-mail richiede autorizzazioni aggiuntive sul tuo token API DockFlare esistente. Aggiornalo in **Profilo utente > Token API** aggiungendo le seguenti autorizzazioni:

| Ambito | Autorizzazione specifica | Livello di accesso | Scopo |
| :--- | :--- | :--- | :--- |
| **Account** | **Workers Scripts** | **Modifica** | Distribuzione dei worker inbound/outbound |
| **Account** | **Workers KV Storage** | **Modifica** | Applicazione delle quote in tempo reale all'edge |
| **Account** | **R2 Storage** | **Modifica** | Creazione e gestione dei bucket di transito |
| **Account** | **Access: Apps and Policies** | **Modifica** | Creare un bypass per il percorso del webhook e-mail in entrata quando Webmail è protetto da Cloudflare Access |
| **Zona** | **Email Routing** | **Modifica** | Attivazione del routing e gestione delle regole |
| **Zona** | **DNS** | **Modifica** | Creazione di record MX, SPF, DMARC e DKIM |

> **Nota di sicurezza:** È consigliato limitare le «Risorse account» e le «Risorse zona» di questo token solo all'account e ai domini specifici che intendi utilizzare con DockFlare.

## Requisiti di sistema

*   **DockFlare:** v3.1.0 o successivo.
*   **Docker:** v20.10+.
*   **Docker Compose:** v2.20+ (richiesto per il supporto dei `profiles`).
*   **Archiviazione:** Assicurati di avere spazio su disco sufficiente sul host per il volume `mail_data`, che conterrà tutti i database e gli allegati delle e-mail.
