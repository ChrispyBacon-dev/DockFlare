# Benvenuti nella documentazione di DockFlare!

DockFlare è un controller ingress self-hosted che semplifica la gestione di Cloudflare Tunnel e Zero Trust. Utilizza le etichette Docker per la configurazione automatica e offre un'interfaccia web solida per definire manualmente i servizi e applicare override alle policy.

Questa documentazione fornisce informazioni complete su DockFlare. Che tu sia un nuovo utente o un utente esperto, troverai tutto ciò che devi sapere per ottenere il massimo da DockFlare.

## Sommario

* **[Home](Home.md)**
* **Per iniziare**
    * [Prerequisiti](Prerequisites.md)
    * [Avvio rapido (Docker Compose)](Quick-Start-Docker-Compose.md)
    * [Accesso all'interfaccia web](Accessing-the-Web-UI.md)
* **Concetti fondamentali**
    * [Come funziona DockFlare](How-DockFlare-Works.md)
    * [Agente DockFlare e architettura multi-server](Multi-Server-Agent.md)
    * [Best practice per le policy di accesso](Access-Policy-Best-Practices.md)
    * [Criteri predefiniti della zona](Zone-Default-Policies.md)
    * [Interno vs Esterno `cloudflared`](Internal-vs-External-cloudflared.md)
    * [Persistenza dello stato](State-Persistence.md)
* **Configurazione**
    * [Etichette dei container](Container-Labels.md)
    * [Fornitori di identità](Identity-Providers.md)
    * [Configurazione provider OAuth](OAuth-Provider-Setup.md)
* **Guida all'uso**
    * [Utilizzo di base (dominio singolo)](Basic-Usage-Single-Domain.md)
    * [Utilizzo di più domini (etichette indicizzate)](Using-Multiple-Domains-Indexed-Labels.md)
    * [Utilizzo di domini wildcard](Using-Wildcard-Domains.md)
    * [Gestione delle zone DNS](Managing-DNS-Zones.md)
    * [Comprendere la Graceful Deletion](Understanding-Graceful-Deletion.md)
    * [Uso dell'interfaccia web](Using-the-Web-UI.md)
    * [Backup e ripristino](Backup-and-Restore.md)
* **Argomenti avanzati**
    * [Modalità `cloudflared` esterna](External-cloudflared-Mode.md)
    * [Passaggio da una modalità all'altra](Switching-Between-Modes.md)
    * [Monitoraggio con Prometheus e Grafana](Monitoring-with-Prometheus-&-Grafana.md)
    * [Ottimizzazione delle prestazioni](Performance-Tuning.md)
    * [Politica di sicurezza dei contenuti (CSP)](Content-Security-Policy.md)
    * [Architettura e rafforzamento della sicurezza](Security-Architecture.md)
* **Risoluzione dei problemi**
    * [Problemi comuni](Common-Issues.md)
    * [Debug e registri](Debugging-&-Logs.md)
    * [Controlli di integrità](Health-Checks.md)
    * [Utilità CLI](CLI-Utilities.md)
* **[Contribuire](Contributing.md)**
* **[Licenza](License.md)**
