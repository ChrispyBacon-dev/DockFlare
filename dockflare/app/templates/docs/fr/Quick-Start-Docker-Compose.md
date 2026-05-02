# Démarrage rapide (Docker Compose)

Ce guide présente le moyen le plus rapide d'exécuter DockFlare avec un socket-proxy renforcé et une configuration Master rootless.

## Option A — Installation en une seule commande (Recommandé)

La façon la plus rapide de démarrer DockFlare est d'utiliser le script d'installation interactif hébergé sur [dockflare.app](https://dockflare.app) :

```bash
bash <(curl -fsSL https://dockflare.app/install.sh)
```

Le script vous guidera à travers :
1. Le choix du répertoire d'installation (par défaut : `~/dockflare/`).
2. Le choix du port local de l'interface (par défaut : `5000`).
3. La configuration optionnelle d'un tunnel Cloudflare pour DockFlare.
4. L'activation optionnelle du profil e-mail (dockflare-mail-manager + dockflare-webmail).

Il génère ensuite le fichier `docker-compose.yml`, vous permet de le vérifier et demande confirmation avant de démarrer le stack.

Une fois démarré, ouvrez `http://<your-server-ip>:5000` et suivez l'assistant de configuration.

---

## Option B — Configuration manuelle avec Docker Compose

### 1. Créez le fichier `docker-compose.yml`

La stack ci-dessous lance `docker-socket-proxy`, initialise le volume persistant avec les bons droits, puis démarre DockFlare avec Redis.

```yaml
services:
  docker-socket-proxy:
    image: tecnativa/docker-socket-proxy:v0.4.1
    container_name: docker-socket-proxy
    restart: unless-stopped
    logging:
      driver: "none"
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
    command: ["sh", "-c", "chown -R ${DOCKFLARE_UID:-65532}:${DOCKFLARE_GID:-65532} /app/data"]
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
      - "5000:5000" # Optional: comment out once exposed via Cloudflare Tunnel with an Access Policy to restrict access to tunnel-only
    #labels: # -- Cloudflare Tunnel Configuration (via DockFlare) OPTIONAL --
      # Main DockFlare with access policy
      #- dockflare.enable=true
      #- dockflare.hostname=dockflare.TLD  # replace with your domain
      #- dockflare.service=http://dockflare:5000
      #- dockflare.access.group=YOUR-ACCESS-GROUP-ID  # your custom access policy
      # -- OAuth Callback Path (Bypass Access Policy) OPTIONAL --
      # Required if using OAuth authentication with access policies on main interface
      #- dockflare.0.hostname=dockflare.example.tld
      #- dockflare.0.path=/auth/google/callback
      #- dockflare.0.service=http://dockflare:5000
      #- dockflare.0.access.group=public-default-bypass

      # Add additional callback paths for other OAuth providers as needed
      # - dockflare.1.hostname=dockflare.example.com
      # - dockflare.1.path=/auth/github/callback
      # - dockflare.1.service=http://dockflare:5000
      # - dockflare.1.access.group=public-default-bypass
    volumes:
      - dockflare_data:/app/data
    environment:
      - REDIS_URL=redis://redis:6379/0
      - REDIS_DB_INDEX=0
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

  redis:
    image: redis:7-alpine
    container_name: dockflare-redis
    restart: unless-stopped
    command: ["redis-server", "--save", "", "--appendonly", "no"]
    logging:
      driver: "none"
    volumes:
      - dockflare_redis:/data
    networks:
      - dockflare-internal

  dockflare-mail-manager:
    image: alplat/dockflare-mail-manager:stable
    container_name: dockflare-mail-manager
    restart: unless-stopped
    profiles: ["email"]
    environment:
      - DOCKFLARE_MASTER_URL=http://dockflare:5000
      - MAIL_DATA_PATH=/data
    volumes:
      - mail_data:/data
    depends_on:
      dockflare:
        condition: service_started
    networks:
      - cloudflare-net
      - dockflare-internal

  dockflare-webmail:
    image: alplat/dockflare-webmail:stable
    container_name: dockflare-webmail
    restart: unless-stopped
    profiles: ["email"]
    environment:
      - DOCKFLARE_MASTER_URL=https://dockflare.TLD  # replace with your domain
    labels:
      - dockflare.enable=true
      - dockflare.hostname=mail.dockflare.TLD  # replace with your domain
      - dockflare.service=http://dockflare-webmail:80
    depends_on:
      dockflare-mail-manager:
        condition: service_started
    networks:
      - cloudflare-net
      - dockflare-internal

volumes:
  dockflare_data:
  dockflare_redis:
  mail_data:

networks:
  cloudflare-net:
    name: cloudflare-net
    external: true
  dockflare-internal:
    name: dockflare-internal
```

**Remarques :**
- Le conteneur Master s'exécute en tant qu'utilisateur `dockflare` (UID/GID 65532). Si vous devez aligner des permissions côté hôte, définissez `DOCKFLARE_UID`/`DOCKFLARE_GID` et reconstruisez l'image, ou ajustez l'init job.
- Le proxy est obligatoire. DockFlare ne monte jamais `/var/run/docker.sock` directement, ce qui limite strictement la surface de l'API Docker exposée au Master.
- Lorsque vous utilisez des montages liés au lieu de volumes nommés, assurez-vous que le répertoire cible est accessible en écriture par l'UID/GID 65532 (ou vos valeurs remplacées).
- Créez une seule fois le réseau externe s'il n'existe pas : `docker network create cloudflare-net`.

### 2. Créer le réseau externe

S'il n'existe pas encore :

```bash
docker network create cloudflare-net
```

### 3. Exécutez DockFlare

Démarrez la pile en mode détaché :

```bash
docker compose up -d
```

Cela fait apparaître le proxy, amorce le volume et lance DockFlare avec Redis.

### 4. Terminez la configuration initiale

Une fois les services exécutés, ouvrez votre navigateur sur `http://<your-server-ip>:5000`.

L'**assistant de configuration initiale** vous guide à travers :
1. Création d'un mot de passe pour l'interface web.
2. Saisie de vos informations d'identification Cloudflare (ID de compte, ID de zone, jeton API).
3. Configuration de votre tunnel Cloudflare initial.
4. *(Facultatif)* Restauration à partir d'une archive de sauvegarde DockFlare. Si vous disposez déjà d'un `dockflare_backup_*.zip`, choisissez **Restaurer à partir d'une sauvegarde** avant l'étape 1 ; l'assistant importe votre configuration et redémarre automatiquement le conteneur.

### 5. Pour les utilisateurs existants (mise à niveau)

Si vous effectuez une mise à niveau à partir d'une version antérieure, DockFlare détecte l'ancien fichier `.env`, migre votre configuration vers le magasin crypté et vous guide dans la création d'un mot de passe. Gardez le proxy de socket en place : les montages directs de `/var/run/docker.sock` ne sont plus pris en charge.
