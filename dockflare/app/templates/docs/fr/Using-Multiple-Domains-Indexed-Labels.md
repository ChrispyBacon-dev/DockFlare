# Utilisation de plusieurs domaines (étiquettes indexées)

DockFlare fournit une fonctionnalité puissante appelée **étiquettes indexées** qui vous permet de définir plusieurs règles d'entrée indépendantes pour un seul conteneur. Ceci est particulièrement utile lorsque vous souhaitez exposer différents ports ou chemins du même service sur différents noms d'hôtes publics.

## Comment ça marche

Pour créer plusieurs règles, il vous suffit de préfixer les étiquettes DockFlare standard avec un entier et un point, en commençant par `0`. Par exemple, `dockflare.0.hostname`, `dockflare.1.hostname`, etc.

* Chaque index (par exemple, `0`, `1`, `2`) représente une règle d'entrée distincte.
* Un nom d'hôte indexé (par exemple, `dockflare.<index>.hostname`) est toujours requis pour lancer une nouvelle règle.
* Les autres étiquettes du même index (par exemple, `dockflare.<index>.service`) s'appliqueront uniquement à cette règle spécifique.

## Le mécanisme de repli

Une caractéristique clé des étiquettes indexées est le mécanisme de secours. Si vous ne fournissez pas d'étiquette indexée spécifique pour une règle, celle-ci **reviendra à la valeur de l'étiquette de base (non indexée) correspondante**.

Cela vous permet de définir des paramètres communs une fois au niveau de base et de remplacer uniquement les valeurs spécifiques qui doivent changer pour chaque règle indexée.

## Exemple : exposer une interface web et une API

Supposons que vous disposiez d'un seul conteneur qui serve à la fois une application web sur le port `80` et une API distincte sur le port `3000`. Vous souhaitez les exposer respectivement sur `app.example.com` et `api.example.com`. Vous souhaitez également sécuriser l'API avec un groupe d'accès spécifique, tandis que l'application principale reste publique.

Voici comment configurer cela à l’aide d’étiquettes indexées :

```yaml
services:
  my-app:
    image: my-application
    restart: unless-stopped
    networks:
      - cloudflare-net
    labels:
      - "dockflare.enable=true"

      # --- Base Labels (Fallback) ---
      # This service is used by rule 0, as it's not specified there.
      - "dockflare.service=http://my-app:80" 

      # --- Rule 0: Main web interface ---
      - "dockflare.0.hostname=app.example.com"
      # No 'service' label here, so it falls back to the base one.
      # No 'access.group' label, so it's public.

      # --- Rule 1: The API ---
      - "dockflare.1.hostname=api.example.com"
      # Override the service to point to the API port.
      - "dockflare.1.service=http://my-app:3000"
      # Add a specific access policy for this rule only.
      - "dockflare.1.access.group=api-users-policy"
```

### Répartition de l'exemple

* **Règle 0 (`app.example.com`)** :
    * Il définit `dockflare.0.hostname`.
    * Il ne définit pas `dockflare.0.service`, il revient donc à la base `dockflare.service` et utilise `http://my-app:80`.
    * Il s'agit d'un service public car aucune politique d'accès n'est définie pour cet index ou au niveau de base.

* **Règle 1 (`api.example.com`)** :
    * Il définit `dockflare.1.hostname`.
    * Il **remplace** le service avec `dockflare.1.service`, pointant vers le port API `3000`.
    * Il applique une politique de sécurité spécifique en utilisant `dockflare.1.access.group`. Cette étiquette n'affecte que cette règle.

Cette approche maintient la configuration de vos étiquettes propre et évite les répétitions, rendant vos fichiers `docker-compose.yml` plus faciles à lire et à gérer.
