# Comprendre la suppression progressive

Lorsque vous arrêtez un conteneur géré par DockFlare, vous remarquerez peut-être que son nom d'hôte public correspondant ne se déconnecte pas immédiatement. Cela est dû à une fonctionnalité appelée **Suppression gracieuse**.

## Qu'est-ce que la suppression progressive ?

Au lieu de supprimer instantanément la règle d'entrée Cloudflare et l'enregistrement DNS au moment où un conteneur s'arrête, DockFlare marque la règle comme **"en attente de suppression"** et démarre un minuteur.

Les ressources Cloudflare associées (la règle d'entrée et l'enregistrement DNS) ne seront définitivement supprimées qu'après l'expiration de ce délai, appelé **délai de grâce**.

## Pourquoi est-ce utile ?

Cette fonctionnalité est conçue pour éviter les interruptions de service dans des scénarios opérationnels courants :

* **Mises à jour du conteneur :** Lorsque vous mettez à jour une image de conteneur (`docker compose up -d`), Docker arrête généralement l'ancien conteneur et en démarre un nouveau. Sans délai de grâce, votre service serait inaccessible pendant une courte période. Avec une suppression progressive, l'enregistrement DNS et la règle d'entrée restent actifs et DockFlare les réassocie simplement au nouveau conteneur, ce qui entraîne aucun temps d'arrêt.
* **Redémarrages temporaires :** Si vous devez arrêter un conteneur pendant un moment pour modifier un paramètre, puis le redémarrer, la période de grâce garantit que votre configuration publique reste intacte.

## La variable `GRACE_PERIOD_SECONDS`

La durée de cette période de grâce est contrôlée par la variable d'environnement `GRACE_PERIOD_SECONDS`, que vous pouvez définir dans votre fichier `docker-compose.yml`.

* La valeur par défaut est `600` secondes (10 minutes).
* Vous pouvez ajuster cette valeur en fonction de vos besoins. Une période plus courte accélère le nettoyage, tandis qu'une période plus longue offre une fenêtre plus grande pour le redémarrage du conteneur.

**Exemple :**
```yaml
services:
  dockflare:
    image: alplat/dockflare:stable
    # ... other settings
    environment:
      - GRACE_PERIOD_SECONDS=3600 # Set a 1-hour grace period
```

## Comment ça marche en pratique

1. **Conteneur arrêté :** Vous exécutez `docker stop my-app`.
2. **En attente de suppression :** DockFlare détecte l'événement d'arrêt. Dans l'interface web, la règle pour `my-app.example.com` affichera désormais son statut comme **"ending_deletion"** et affichera l'heure à laquelle sa suppression est planifiée.
3. **Les deux scénarios :**
    * **Scénario A : expiration du délai de grâce :** Si le conteneur reste arrêté et que le délai de grâce (par exemple 10 minutes) expire, la tâche de nettoyage en arrière-plan de DockFlare s'exécutera. Cela supprimera la règle d'entrée de votre tunnel Cloudflare et supprimera l'enregistrement DNS CNAME.
    * **Scénario B : redémarrage du conteneur :** Si vous redémarrez le conteneur (`docker start my-app`) **avant** l'expiration du délai de grâce, DockFlare détectera l'événement de démarrage. Il verra que la règle est en attente de suppression, annulera la suppression et redéfinira son statut sur **"active"**. Votre service continue de fonctionner de manière transparente.
