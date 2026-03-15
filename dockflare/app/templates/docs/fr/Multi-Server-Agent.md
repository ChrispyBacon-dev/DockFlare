# Agent DockFlare et architecture multiserveur

DockFlare 3.0 introduit un modèle d'exécution distribué qui vous permet de gérer des tunnels Cloudflare sur plusieurs hôtes Docker. Le **Master** de DockFlare coordonne la configuration, tandis que des **Agents** légers s'exécutent aux côtés de vos charges de travail et maintiennent leur instance locale de `cloudflared` synchronisée.

Ce guide explique l'architecture, le modèle de sécurité et le flux de travail pas à pas pour déployer des agents.

---

## Pourquoi utiliser des agents ?

* **Séparer l'exécution de la couche d'ingress** : gardez les charges de travail proches des utilisateurs tout en conservant un plan de contrôle unique.
* **Visibilité par hôte** : surveillez le heartbeat, l'état du tunnel et l'historique des commandes de chaque agent.
* **Jetons de moindre privilège** : révoquez un agent compromis sans toucher au Master ni aux autres hôtes.
* **Mises à jour résilientes** : les agents continuent de servir le trafic avec leur dernière configuration connue si le Master est temporairement indisponible.

---

## Composants en un coup d'œil

| Composant | Responsabilité |
|-----------|----------------|
| **Master (DockFlare)** | Héberge l'interface web, stocke l'état, aligne les règles d'ingress souhaitées et émet des commandes. |
| **Redis** | Couche partagée pour le cache, les heartbeats des agents et les commandes en file d'attente. |
| **DockFlare Agent** | Conteneur sans interface qui surveille les événements Docker locaux, exécute des commandes et gère `cloudflared`. |
| **cloudflared** | Gère la connexion réelle du tunnel vers Cloudflare pour chaque agent. |

Le Master et Redis s'exécutent généralement ensemble, tandis que les agents s'exécutent à côté des charges de travail, potentiellement sur des réseaux distants.

---

## Prérequis

* DockFlare Master ≥ v3.0 avec Redis configuré (`REDIS_URL` défini). Vous pouvez aussi préciser `REDIS_DB_INDEX` pour isoler les données d'autres conteneurs utilisant la même instance Redis.
* Jeton API Cloudflare avec autorisations Tunnel + Access, identiques aux versions précédentes.
* Environnement Docker sur chaque hôte que vous prévoyez de gérer.
* (Facultatif) Segment réseau dédié ou VPN entre le Master et les agents si vous n'exposez pas le Master publiquement.

---

## Vue d'ensemble du flux de travail

1. **Générez une clé API d'agent** dans l'interface DockFlare (`Agents → Generate Key`).
2. **Déployez le conteneur DockFlare Agent** sur l'hôte distant en lui fournissant l'URL du Master et la clé.
3. L'agent **s'enregistre** auprès du Master et apparaît avec l'état *Pending*.
4. Depuis l'interface du Master, **approuvez** l'agent et attribuez-lui, ou créez, un tunnel Cloudflare pour cet hôte.
5. Le Master met les commandes en file d'attente ; l'agent les récupère régulièrement, applique la configuration et remonte son état ainsi que son heartbeat. DockFlare détecte automatiquement la zone cible pour chaque nom d'hôte et ne revient à la zone par défaut qu'en cas d'échec de la détection.
6. Lorsque des conteneurs démarrent ou s'arrêtent sur l'hôte de l'agent, celui-ci renvoie les événements vers le Master, qui met à jour le DNS, les politiques Access et les règles d'ingress du tunnel.

---

## Déploiement du DockFlare Agent

> ℹ️ L'agent sera publié sous le nom `alplat/dockflare-agent`. Tant que le dépôt public n'est pas disponible, vous pouvez le construire à partir de l'arborescence source `DockFlare-agent` incluse avec DockFlare 3.0.

```bash
# Example environment file used by the agent container
DOCKFLARE_MASTER_URL=https://dockflare.example.com
DOCKFLARE_API_KEY=agent_api_key_goes_here
DOCKER_HOST=tcp://docker-socket-proxy:2375
# control the docker image used for the managed cloudflared tunnel (accepts repo:tag or repo@sha256:<digest>)
CLOUDFLARED_IMAGE=cloudflare/cloudflared:2025.9.0
LOG_LEVEL=info
TZ=Europe/Zurich
```

`docker-compose.yml` minimal sur l'hôte de l'agent :

```yaml
version: '3.8'

services:
  docker-socket-proxy:
    image: tecnativa/docker-socket-proxy:v0.4.1
    container_name: docker-socket-proxy
    restart: unless-stopped
    environment:
      - DOCKER_HOST=unix:///var/run/docker.sock
      - CONTAINERS=1
      - EVENTS=1
      - NETWORKS=1
      - IMAGES=1
      - POST=1
      - PING=1
      - EXEC=1
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock
    networks:
      - dockflare-internal
      
  dockflare-agent:
    image: alplat/dockflare-agent:latest
    container_name: dockflare-agent
    restart: unless-stopped
    env_file:
      - .env
    environment:
      - DOCKER_HOST=${DOCKER_HOST:-tcp://docker-socket-proxy:2375}
      - TZ=${TZ:-UTC}
      - LOG_LEVEL=${LOG_LEVEL:-info}
    volumes:
      - agent_data:/app/data
    depends_on:
      - docker-socket-proxy
    networks:
      - cloudflare-net
      - dockflare-internal

volumes:
  agent_data:

networks:
  cloudflare-net:
    name: cloudflare-net
    external: true
  dockflare-internal:
    name: dockflare-internal
```

- Exécutez `docker network create cloudflare-net` une seule fois pour provisionner le réseau partagé utilisé par le Master et les agents.
- Le proxy de socket limite la surface de l'API Docker accessible à l'agent ; seules les capacités définies sur `1` sont exposées.
- L'image de l'agent s'exécute sous l'utilisateur non privilégié `dockflare` (UID/GID 65532). Assurez-vous que les répertoires montés, comme `/app/data`, sont accessibles en écriture par ce compte ou reconstruisez avec `DOCKFLARE_UID/DOCKFLARE_GID` pour qu'ils correspondent à votre hôte.
- Remplissez un fichier `.env` avec `DOCKFLARE_MASTER_URL` et `DOCKFLARE_API_KEY` ; des surcharges facultatives, comme `LOG_LEVEL` ou `DOCKER_HOST`, peuvent être fournies de la même manière.

---

## Modèle de sécurité

* **Clé API du Master** : protège l'API d'administration. L'interface ne l'affiche qu'après un clic sur *Show master API key*.
* **Clés API d'agent** : uniques par agent. Révoquer une clé bloque immédiatement toute nouvelle inscription ou commande depuis cet hôte.
* **Redis** : utilisé pour les files d'attente et les caches ; sécurisez-le avec un mot de passe et des ACL réseau s'il s'exécute en dehors d'un LAN de confiance.
* **Transport** : exécutez le Master derrière HTTPS, par exemple via Cloudflare Access, afin que le trafic des agents soit chiffré.
* **Exécution de moindre privilège** : le conteneur de l'agent s'exécute sous l'utilisateur `dockflare` (UID/GID 65532) et s'appuie sur le proxy de socket pour limiter l'accès à Docker à l'inspection des conteneurs et au contrôle du cycle de vie.

### Renforcement recommandé

1. Stockez les clés des agents dans un coffre-fort ou un gestionnaire de mots de passe et faites-les tourner régulièrement.
2. **Ne désactivez pas la connexion par mot de passe**. Utilisez plutôt des fournisseurs OAuth/OIDC pour bénéficier du single sign-on sans compromettre la sécurité. Si vous devez la désactiver, gardez à l'esprit que cela crée une vulnérabilité réseau Docker : n'importe quel conteneur sur le même réseau peut contourner l'authentification externe. Consultez [Accès à l'interface web](Accessing-the-Web-UI.md) pour connaître toutes les implications de sécurité.
3. Utilisez des tunnels séparés par agent afin de conserver une isolation de moindre privilège.
4. Surveillez la page `Agents` pour détecter les trous dans le heartbeat ; les nœuds hors ligne peuvent être supprimés directement depuis l'interface.

---

## Dépannage

| Symptôme | Correctif |
|---------|-----|
| Agent bloqué dans `pending` | Assurez-vous qu'il s'est enregistré avec la bonne clé API puis approuvez-le depuis l'interface. |
| Les commandes ne disparaissent jamais | Vérifiez la connectivité Redis et la synchronisation des horloges des conteneurs d'agents. |
| Le DNS ne se met pas à jour | Le Master doit pouvoir joindre Cloudflare et l'agent doit envoyer les événements de conteneurs ; vérifiez `docker logs dockflare-agent`. |
| Heartbeat hors ligne | Vérifiez le chemin réseau entre l'agent et le Master ; les problèmes de pare-feu ou de TLS sont fréquents. |

---

## Étapes suivantes

* Consultez le guide de démarrage rapide mis à jour dans le README du dépôt afin de confirmer que Redis est configuré.
* Consultez le journal des modifications pour voir les changements incompatibles et les notes de migration.
* Abonnez-vous au dépôt public DockFlare Agent lorsqu'il sera publié afin de rester à jour sur les versions.

Bonne gestion des tunnels.
