# Persistance de l'état

DockFlare est une application avec état. Il doit garder une trace des services qu'il gère, des remplacements de l'interface utilisateur et d'autres détails de configuration. Cet état est conservé sur le disque pour garantir que votre configuration ne soit pas perdue si le conteneur DockFlare est redémarré ou recréé.

## Comment l'état est stocké

DockFlare stocke son état dans trois fichiers clés situés dans le répertoire `/app/data` à l'intérieur du conteneur :

1. `dockflare_config.dat` : Il s'agit du fichier le plus critique. Il contient tous vos paramètres principaux et informations sensibles dans un format **crypté**. Cela comprend :
    * Votre jeton API Cloudflare et votre identifiant de compte.
    * Le hachage de votre mot de passe de l'interface utilisateur DockFlare.
    * Paramètres de base configurés via l'interface utilisateur, tels que le nom du tunnel et les identifiants de zone.

2. `agent_keys.dat` : un magasin chiffré contenant toutes les clés API de l'agent et leurs métadonnées (propriétaire, statut, horodatages). Garder ce fichier en sécurité empêche la réutilisation de clés obsolètes.

3. `state.json` : ce fichier stocke l'état dynamique de vos services gérés au format JSON simple. Cela comprend :
    * La liste de toutes les règles d'entrée gérées par DockFlare, qu'elles proviennent d'étiquettes Docker ou qu'elles aient été créées manuellement dans l'interface utilisateur.
    * Tout remplacement de l'interface utilisateur appliqué aux politiques d'accès.
    * Tous les groupes d'accès que vous avez créés.
    * Le statut « en attente de suppression » pour les services qui ont été arrêtés mais qui sont toujours dans leur délai de grâce.

## L'importance d'un volume persistant

Étant donné que toute votre configuration est stockée dans le répertoire `/app/data`, il est **absolument crucial** que vous mappiez ce répertoire à un volume persistant sur votre machine hôte.

Si vous n'utilisez pas de volume persistant, **tous vos paramètres, mot de passe de l'interface utilisateur et configurations de règles seront perdus** chaque fois que le conteneur DockFlare est supprimé et recréé (par exemple, lorsque vous mettez à jour l'image).

### Configuration Docker Compose recommandée

La configuration `docker-compose.yml` recommandée gère cela automatiquement en définissant un volume nommé et en le montant sur `/app/data` :

```yaml
services:
  dockflare:
    # ... other settings
    volumes:
      # This line ensures your data is persisted
      - ./dockflare_data:/app/data

volumes:
  # This defines the named volume on your host
  dockflare_data:
```

Avec cette configuration, vos fichiers `dockflare_config.dat`, `agent_keys.dat` et `state.json` seront stockés dans un répertoire nommé `dockflare_data` sur votre hôte, préservant ainsi votre configuration en toute sécurité lors des mises à jour du conteneur.

## Sauvegarde et restauration

DockFlare regroupe désormais toutes les données critiques dans une seule archive de sauvegarde cryptée. Les caches Redis sont omis car ils peuvent être reconstruits en toute sécurité sur le réseau privé `dockflare-internal`. Le panneau **Paramètres → Sauvegarde et restauration** vous permet de télécharger un `.zip` qui contient :

* `dockflare_config.dat`
* `dockflare.key`
* `agent_keys.dat`
* `state.json` (si présent)
* Un manifeste avec des sommes de contrôle pour la vérification de l'intégrité

La restauration de l'archive recrée ces fichiers et les recharge dans l'instance en cours d'exécution. Les anciens téléchargements `state.json` sont toujours acceptés, mais ils restaurent uniquement les métadonnées des règles. Vous devrez ensuite saisir à nouveau les informations d'identification manuellement.
DockFlare redémarre automatiquement le conteneur après une restauration complète de l'archive afin que la configuration chiffrée soit chargée immédiatement.