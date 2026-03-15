# Utilisation de base (domaine unique)

Ce guide présente le cas d'utilisation le plus courant de DockFlare : exposer un seul conteneur Docker à Internet sur un nom d'hôte public.

## Prérequis

Avant de commencer, assurez-vous d'avoir :
1. Vous avez terminé le guide [Démarrage rapide](Quick-Start-Docker-Compose.md).
2. DockFlare est en cours d'exécution et connecté à votre compte Cloudflare.
3. Vous souhaitez exposer un service (nous utiliserons `nginx` dans cet exemple).

## Exemple : Exposer un conteneur NGINX

Supposons que vous souhaitiez exposer un serveur Web NGINX standard sous le nom d'hôte `nginx.example.com`.

### 1. Ajoutez le service à votre `docker-compose.yml`

Modifiez votre fichier `docker-compose.yml` pour inclure le service `nginx`. La clé est d'ajouter les étiquettes `dockflare.*` à sa configuration.

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
      - INFO=1
      - EXEC=1
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock
    networks:
      - dockflare-internal

  dockflare-init:
    image: alpine:3.20
    command: ["sh", "-c", "chown -R 65532:65532 /app/data"]
    volumes:
      - dockflare_data:/app/data
    networks:
      - dockflare-internal
    restart: "no"

  dockflare:
    image: alplat/dockflare:stable
    container_name: dockflare
    restart: unless-stopped
    ports:
      - "5000:5000"
    volumes:
      - dockflare_data:/app/data
    environment:
      - REDIS_URL=redis://redis:6379/0
      - REDIS_DB_INDEX=0  # Optional: specify Redis database index (0-15) for isolation from other containers
      - DOCKER_HOST=tcp://docker-socket-proxy:2375
    depends_on:
      docker-socket-proxy:
        condition: service_started
      dockflare-init:
        condition: service_completed_successfully
      redis:
        condition: service_started
    networks:
      - cloudflare-net
      - dockflare-internal

  # Add your new service here
  nginx-webserver:
    image: nginx:latest
    container_name: my-nginx
    restart: unless-stopped
    networks:
      - cloudflare-net
    labels:
      - "dockflare.enable=true"
      - "dockflare.hostname=nginx.example.com"
      - "dockflare.service=http://nginx-webserver:80"
      # Optional: Apply public access with zone protection bypass
      - "dockflare.access.group=public-default-bypass"

  redis:
    image: redis:7-alpine
    container_name: dockflare-redis
    restart: unless-stopped
    command: ["redis-server", "--save", "", "--appendonly", "no"]
    volumes:
      - dockflare_redis:/data
    networks:
      - dockflare-internal

volumes:
  dockflare_data:
  dockflare_redis:

networks:
  cloudflare-net:
    name: cloudflare-net
    external: true
  dockflare-internal:
    name: dockflare-internal
```
> **Pourquoi Redis ?** DockFlare s'appuie sur Redis pour la mise en cache, la diffusion de journaux et la messagerie cross-thread. L'exécuter sur le réseau privé `dockflare-internal` permet à Redis d'être accessible uniquement par DockFlare, tandis que les charges de travail restent isolées sur `cloudflare-net`.


### 2. Comprendre les étiquettes

* `dockflare.enable=true` : ceci indique à DockFlare de gérer ce conteneur.
* `dockflare.hostname=nginx.example.com` : Il s'agit de l'URL publique où votre service sera disponible. DockFlare créera un enregistrement DNS pour ce nom d'hôte dans votre compte Cloudflare.
* `dockflare.service=http://nginx-webserver:80` : ceci indique à Cloudflare Tunnel où envoyer le trafic. C'est l'adresse interne du conteneur NGINX. Notez que nous utilisons le nom du service (`nginx-webserver`) comme nom d'hôte, ce qui est possible car les deux conteneurs sont sur le même réseau Docker.
* `dockflare.access.group=public-default-bypass` : (Facultatif) utilise la stratégie de contournement du système pour garantir l'accès public même si une stratégie de protection `*.example.com` au niveau de la zone existe. Ceci est important lorsque vous disposez de politiques génériques protégeant votre domaine mais que vous avez besoin de services spécifiques pour rester publics.

### 3. Déployer le service

Enregistrez votre fichier `docker-compose.yml` et exécutez la commande suivante pour démarrer le nouveau service :

```bash
docker compose up -d
```

### 4. Vérification

DockFlare détectera le nouveau conteneur et effectuera automatiquement les actions suivantes :
1. Ajoutez une règle d'entrée à votre tunnel Cloudflare pour `nginx.example.com`.
2. Créez un enregistrement CNAME pour `nginx.example.com` dans votre DNS Cloudflare, pointant vers le tunnel.

Vous pouvez le vérifier de plusieurs manières :
* **Interface web DockFlare** : le service `nginx.example.com` apparaîtra sur le tableau de bord.
* **Cloudflare Dashboard** : vous verrez le nouvel enregistrement CNAME dans vos paramètres DNS et la nouvelle règle d'entrée dans la configuration de votre tunnel.

Après quelques instants pour que DNS se propage, vous devriez pouvoir accéder à `https://nginx.example.com` dans votre navigateur et voir la page d'accueil NGINX par défaut.

## Sauvegarde et restauration approfondie

DockFlare est livré avec un flux de sauvegarde de première classe afin que vous puissiez déplacer ou récupérer une instance en quelques minutes.

### Ce que contient l'archive de sauvegarde

Lorsque vous téléchargez une sauvegarde depuis **Paramètres → Sauvegarde et restauration** (ou l'assistant d'intégration), DockFlare génère un `.zip` avec les fichiers suivants :

| Fichier | Descriptif |
| --- | --- |
| `dockflare_config.dat` | Charge utile de configuration cryptée (informations d'identification Cloudflare, hachage du mot de passe de l'interface utilisateur, valeurs par défaut du tunnel, clé API principale, etc.). |
| `dockflare.key` | La clé Fernet utilisée pour déchiffrer `dockflare_config.dat` et d'autres charges utiles chiffrées. Conservez-le avec les archives. |
| `agent_keys.dat` | Registre crypté des clés API d'agent, des métadonnées et de l'état de révocation. |
| `state.json` | Instantané JSON simple de l'état d'exécution : règles gérées, agents, groupes d'accès. Ceci est inclus afin que les opérateurs puissent inspecter ou migrer des pièces spécifiques si nécessaire. |
| `manifest.json` | Sommes de contrôle et informations de version pour chaque fichier de l’archive. |

La sauvegarde est autonome : sa restauration via l'assistant/appliquer le point de terminaison écrit chaque fichier dans `/app/data/` et planifie immédiatement un redémarrage du conteneur afin que la configuration chiffrée soit rechargée au démarrage.

### Notes de restauration et de compatibilité

- **Interface utilisateur de l'assistant et des paramètres** : téléchargez le `.zip` et DockFlare l'importera, rechargera l'état et quittera. Docker redémarre automatiquement le conteneur, vous permettant ainsi de revenir en mode opérationnel sans intervention manuelle.
- **Legacy `state.json`** : pour le dépannage ou les flux de travail avancés, vous pouvez toujours télécharger uniquement un fichier `state.json`. DockFlare remplira l'état d'exécution à partir de celui-ci mais ignorera la configuration chiffrée ; vous devrez ensuite ressaisir vos informations d'identification.
- **Automation** : le redémarrage étant automatique, assurez-vous que toutes les vérifications de l'état du proxy inverse autorisent une brève fenêtre de redémarrage (~ 5 s) après une restauration.

Les sauvegardes n'incluent **pas** l'ensemble de données Redis ; il met uniquement en cache les données que DockFlare peut recalculer. Le volume `/app/data` à côté de l’archive est l’élément essentiel à sécuriser et à sauvegarder.
