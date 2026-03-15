# Bienvenue dans la documentation DockFlare !

DockFlare est un contrôleur d'ingress auto-hébergé qui simplifie la gestion de Cloudflare Tunnel et de Zero Trust. Il utilise les labels Docker pour l'automatisation, tout en fournissant une interface web robuste pour les définitions de services manuelles et les surcharges de politiques.

Cette documentation couvre DockFlare de bout en bout. Que vous démarriez ou que vous exploitiez déjà DockFlare en production, vous y trouverez les informations essentielles.

## Table des matières

* **[Accueil](Home.md)**
* **Mise en route**
    * [Prérequis](Prerequisites.md)
    * [Démarrage rapide (Docker Compose)](Quick-Start-Docker-Compose.md)
    * [Accès à l'interface web](Accessing-the-Web-UI.md)
* **Concepts clés**
    * [Comment fonctionne DockFlare](How-DockFlare-Works.md)
    * [Agent DockFlare et architecture multiserveur](Multi-Server-Agent.md)
    * [Meilleures pratiques en matière de politique d'accès](Access-Policy-Best-Practices.md)
    * [Politiques de zone par défaut](Zone-Default-Policies.md)
    * [`cloudflared` interne vs externe](Internal-vs-External-cloudflared.md)
    * [Persistance de l'état](State-Persistence.md)
* **Configuration**
    * [Étiquettes des conteneurs](Container-Labels.md)
    * [Fournisseurs d'identité](Identity-Providers.md)
    * [Configuration du fournisseur OAuth](OAuth-Provider-Setup.md)
* **Guide d'utilisation**
    * [Utilisation de base (domaine unique)](Basic-Usage-Single-Domain.md)
    * [Utilisation de plusieurs domaines (étiquettes indexées)](Using-Multiple-Domains-Indexed-Labels.md)
    * [Utilisation de domaines wildcard](Using-Wildcard-Domains.md)
    * [Gestion des zones DNS](Managing-DNS-Zones.md)
    * [Comprendre la suppression progressive](Understanding-Graceful-Deletion.md)
    * [Utilisation de l'interface web](Using-the-Web-UI.md)
    * [Sauvegarde et restauration](Backup-and-Restore.md)
* **Sujets avancés**
    * [Mode `cloudflared` externe](External-cloudflared-Mode.md)
    * [Basculer entre les modes](Switching-Between-Modes.md)
    * [Surveillance avec Prometheus & Grafana](Monitoring-with-Prometheus-&-Grafana.md)
    * [Réglage des performances](Performance-Tuning.md)
    * [Politique de sécurité du contenu (CSP)](Content-Security-Policy.md)
    * [Architecture de sécurité et renforcement](Security-Architecture.md)
* **Dépannage**
    * [Problèmes courants](Common-Issues.md)
    * [Débogage et journaux](Debugging-&-Logs.md)
    * [Vérifications d'état](Health-Checks.md)
    * [Utilitaires CLI](CLI-Utilities.md)
* **[Contribuer](Contributing.md)**
* **[Licence](License.md)**
