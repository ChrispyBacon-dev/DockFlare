# Bilans de santé

DockFlare comprend un point de terminaison de vérification de l'état dédié qui peut être utilisé avec le mécanisme de vérification de l'état intégré de Docker. Cela permet à Docker de surveiller la santé de l'application DockFlare et de la redémarrer automatiquement si elle ne répond plus.

## Le point de terminaison `/ping`

DockFlare expose un simple point de terminaison HTTP à `/ping`.

* **Objectif :** Fournir aux systèmes automatisés un moyen simple de vérifier si le serveur Web DockFlare est en cours d'exécution et réactif.
* **Authentification :** Ce point de terminaison est **exempt d'authentification**. Vous n'avez pas besoin d'être connecté pour y accéder, ce qui permet au mécanisme de vérification de l'état interne de Docker de l'utiliser.
* **Réponse saine :** Une application DockFlare saine et en cours d'exécution répondra à une demande à `/ping` avec un code d'état **HTTP 200 OK**.
* **Informations sur la version :** Le corps de la réponse du point de terminaison `/ping` contient également la version en cours d'exécution de l'application DockFlare.

## Comment configurer un bilan de santé dans Docker Compose

Vous pouvez ajouter une section `healthcheck` au service `dockflare` dans votre fichier `docker-compose.yml` pour que Docker surveille automatiquement l'état de santé de l'application.

```yaml
services:
  dockflare:
    image: alplat/dockflare:stable
    container_name: dockflare
    restart: unless-stopped
    # ... other settings
    healthcheck:
      # The command to run to check health.
      # curl is used to make an HTTP request to the ping endpoint.
      test: ["CMD", "curl", "-f", "http://localhost:5000/ping"]
      # How often to run the check
      interval: 1m30s
      # How long to wait for a response
      timeout: 10s
      # How many consecutive failures before marking as unhealthy
      retries: 3
      # How long to wait after the container starts before running the first check
      start_period: 40s
```

### Décomposition de la configuration `healthcheck` :

* `test` : il s'agit de la commande que Docker exécute à l'intérieur du conteneur. `curl -f` effectuera une requête HTTP au point de terminaison `/ping` et se terminera avec un code d'état différent de zéro si la réponse n'est pas HTTP 200 OK.
* `interval` : Docker exécutera cette vérification toutes les 90 secondes.
* `timeout` : Docker attendra jusqu'à 10 secondes pour que la commande soit terminée.
* `retries` : si la vérification échoue 3 fois de suite, Docker marquera le conteneur comme `unhealthy`.
* `start_period` : Docker attendra 40 secondes après le démarrage du conteneur avant d'effectuer le premier contrôle de santé. Cela donne à l’application le temps de s’initialiser correctement.

Une fois cette configuration en place, vous pouvez vérifier la santé de votre conteneur en exécutant `docker ps`. La colonne d'état affichera `(healthy)` si le contrôle de santé réussit. Si le conteneur devient défectueux, Docker le redémarrera automatiquement en fonction de la stratégie `restart` (par exemple, `unless-stopped`).