# Utilisation de domaines génériques

DockFlare prend en charge l'utilisation de domaines génériques (par exemple, `*.example.com`) pour acheminer le trafic de plusieurs sous-domaines vers un seul service. Ceci est particulièrement utile pour les applications qui gèrent des sous-domaines dynamiques, tels que les services multi-tenants ou les tableaux de bord personnels comme Heimdall.

## Comment ça marche

Lorsque vous utilisez un nom d'hôte générique, Cloudflare Tunnel acheminera tout le trafic de tout sous-domaine qui n'a pas d'enregistrement DNS plus spécifique vers le service que vous spécifiez.

Par exemple, si vous configurez `*.apps.example.com`, le trafic pour `service1.apps.example.com`, `service2.apps.example.com`, etc. sera tous acheminé vers le même conteneur de destination.

## Considérations importantes

Contrairement aux noms d'hôte classiques, DockFlare **ne peut pas créer automatiquement d'enregistrements DNS pour les domaines génériques**. Vous devez créer manuellement l'enregistrement DNS générique dans votre tableau de bord Cloudflare.

DockFlare gérera toujours la **règle d'entrée** dans votre tunnel Cloudflare, mais la configuration DNS initiale est une étape manuelle.

## Guide étape par étape

Voici comment configurer correctement un domaine générique avec DockFlare, en utilisant `*.plex.example.com` comme exemple.

### Étape 1 : Créer manuellement l'enregistrement DNS générique

1. Connectez-vous à votre **Tableau de bord Cloudflare**.
2. Accédez aux paramètres DNS de votre domaine.
3. Cliquez sur **Ajouter un enregistrement** et créez un enregistrement CNAME avec les détails suivants :
    * **Type :** `CNAME`
    * **Nom :** `*.plex` (ou simplement `*` si votre domaine principal est `plex.example.com`)
    * **Cible :** Le nom d'hôte public de votre tunnel. Vous pouvez le trouver dans votre tableau de bord Cloudflare Zero Trust sous **Accès -> Tunnels**. Cela ressemblera à quelque chose comme `your-tunnel-uuid.cfargotunnel.com`.
    * **Statut du proxy :** Assurez-vous qu'il est **Proxy** (nuage orange).

    Cet enregistrement DNS manuel indique à Cloudflare d'envoyer tout le trafic pour `*.plex.example.com` vers votre tunnel.

### Étape 2 : Configurez votre service avec une étiquette générique

Maintenant, configurez votre service dans votre fichier `docker-compose.yml` avec une étiquette de nom d'hôte générique.

```yaml
services:
  my-proxy-manager:
    image: nginxproxymanager/nginx-proxy-manager
    restart: unless-stopped
    networks:
      - cloudflare-net
    labels:
      - "dockflare.enable=true"
      # Use the wildcard hostname here
      - "dockflare.hostname=*.plex.example.com"
      - "dockflare.service=http://my-proxy-manager:81"
```

### Étape 3 : Déployer et vérifier

1. Enregistrez votre fichier `docker-compose.yml` et exécutez `docker compose up -d`.
2. DockFlare détectera le conteneur et créera une règle d'entrée dans votre tunnel Cloudflare pour le nom d'hôte `*.plex.example.com`.
3. Vous pouvez le vérifier dans l'interface web de DockFlare et dans la configuration de votre tunnel dans le tableau de bord Cloudflare.

Désormais, toute requête adressée à un sous-domaine tel que `sonarr.plex.example.com` ou `radarr.plex.example.com` sera acheminée via votre tunnel Cloudflare vers votre conteneur `my-proxy-manager`, qui pourra ensuite gérer le trafic en conséquence.
