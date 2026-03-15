# Gestion des zones DNS

DockFlare est capable de gérer les enregistrements DNS sur plusieurs domaines (zones Cloudflare) au sein du même compte Cloudflare. Cela vous permet d'exécuter des services sur `service-a.domain-one.com` et `service-b.another-domain.org` à partir de la même instance DockFlare.

## Zone par défaut

Lors de la configuration initiale de DockFlare, vous fournissez un **ID de zone**. Il s'agit de la **zone par défaut** où DockFlare créera tous les enregistrements DNS. Si vous envisagez d’utiliser un seul domaine, c’est tout ce dont vous devez vous soucier.

## Remplacer la zone par une étiquette

Pour gérer un service sur un domaine autre que celui par défaut, vous pouvez utiliser le label `dockflare.zonename`.

Cette étiquette indique à DockFlare de créer l'enregistrement DNS pour ce service spécifique dans la zone Cloudflare spécifiée.

### Prérequis

Pour que cela fonctionne, vous devez vous assurer que le **jeton API Cloudflare** que vous utilisez dispose des autorisations `Zone:DNS:Edit` pour **toutes les zones** que vous avez l'intention de gérer.

### Exemple

Disons que votre zone par défaut est `example.com`, mais que vous souhaitez également exécuter un service sur `media.io`.

```yaml
services:
  # This service will be created in the default zone (example.com)
  service-one:
    image: nginx
    labels:
      - "dockflare.enable=true"
      - "dockflare.hostname=nginx.example.com"
      - "dockflare.service=http://service-one:80"

  # This service will be created in the 'media.io' zone
  service-two:
    image: portainer/portainer-ce
    labels:
      - "dockflare.enable=true"
      - "dockflare.hostname=portainer.media.io"
      - "dockflare.service=http://service-two:9000"
      # Override the default zone for this service
      - "dockflare.zonename=media.io"
```

Lorsque vous déployez ceci, DockFlare :
1. Créez un enregistrement CNAME pour `nginx.example.com` dans la zone `example.com`.
2. Créez un enregistrement CNAME pour `portainer.media.io` dans la zone `media.io`.

Les deux noms d'hôte seront ajoutés en tant que règles d'entrée au même tunnel Cloudflare.

## Affichage des enregistrements DNS dans l'interface utilisateur

L'interface web de DockFlare dispose d'une fonctionnalité sur la page **Paramètres** qui vous permet d'afficher tous les tunnels Cloudflare de votre compte et les enregistrements DNS pointant vers eux.

Pour garantir que l'interface utilisateur peut trouver les enregistrements DNS dans toutes vos différentes zones, vous pouvez utiliser la variable d'environnement `TUNNEL_DNS_SCAN_ZONE_NAMES`.

### `TUNNEL_DNS_SCAN_ZONE_NAMES`

Cette variable d'environnement accepte une liste de noms de zones séparés par des virgules que l'interface utilisateur doit analyser lors de la recherche d'enregistrements DNS.

**Exemple `docker-compose.yml` :**
```yaml
services:
  dockflare:
    image: alplat/dockflare:stable
    # ... other settings
    environment:
      # Indiquez à l'interface de scanner aussi ces zones en plus de la zone par défaut
      - TUNNEL_DNS_SCAN_ZONE_NAMES=media.io,another-domain.org
```

Cela garantira que la visionneuse d'enregistrements DNS dans l'interface utilisateur fournit une image complète de tous les domaines pointant vers vos tunnels.
