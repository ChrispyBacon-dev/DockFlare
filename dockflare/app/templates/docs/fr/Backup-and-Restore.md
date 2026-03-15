# Sauvegarde et restauration

DockFlare 3.0 introduit une archive de sauvegarde complète afin que vous puissiez déplacer un maître vers un nouveau matériel, récupérer après une panne ou effectuer des mises à niveau sans toucher au répertoire de données brutes.

## Ce qui est enregistré
- `dockflare.key` – la clé Fernet qui déverrouille chaque fichier crypté.
- `dockflare_config.dat` – informations d'identification Cloudflare chiffrées, comptes de l'interface web et paramètres d'exécution.
- `agent_keys.dat` – clés API d'agent chiffrées et métadonnées d'audit.
- `state.json` – miroir JSON simple des règles, des agents et des groupes d'accès.
- `manifest.json` – sommes de contrôle et informations de version pour l'archive (générées automatiquement).

Tous ces fichiers sont regroupés dans un seul `dockflare_backup_YYYYMMDD_HHMMSS.zip`. Conservez le ZIP et les fichiers extraits ensemble ; sans `dockflare.key`, les artefacts chiffrés sont inutiles.

## Création d'une sauvegarde
1. Ouvrez **Paramètres → Sauvegarde et restauration** dans l'interface web principale.
2. Cliquez sur **Télécharger la sauvegarde (.zip)**.
3. Conservez les archives dans un endroit sûr. Traitez-le comme des informations d'identification : il contient tout ce dont vous avez besoin pour contrôler votre compte Cloudflare via DockFlare.

Des sauvegardes peuvent être effectuées pendant que le maître est en cours d'exécution. Chaque archive comprend un manifeste avec des hachages SHA-256 afin que les téléchargements corrompus soient faciles à repérer.

## Restauration sur un maître existant
1. Accédez à **Paramètres → Sauvegarde et restauration**.
2. Téléchargez le `.zip` via **Restaurer à partir d'une sauvegarde**.
3. Confirmez l'avertissement : la restauration écrase la configuration, les clés d'agent et les règles.

DockFlare restaure les fichiers chiffrés, recharge `state.json` et, si nécessaire, écrit un indicateur de redémarrage. Le conteneur s'arrête quelques secondes plus tard pour que Docker puisse le relancer avec la nouvelle configuration. L'interface web se rouvre ensuite avec les identifiants restaurés.

Les anciens fichiers `state.json` sont toujours acceptés pour les restaurations partielles. Le téléchargement d'un fichier JSON nu remplace uniquement les règles et ignore la configuration chiffrée.

## Restauration pendant l'assistant d'installation
Les nouvelles installations proposent désormais un lien **Restaurer à partir d'une sauvegarde** avant l'étape 1 de l'assistant de pré-vérification.

1. Téléchargez le ZIP de sauvegarde.
2. DockFlare écrit les artefacts et l'état chiffrés sur le disque.
3. Le conteneur redémarre automatiquement ; à son retour, connectez-vous avec le compte administrateur restauré.

Ce flux constitue le moyen le plus rapide de cloner un maître de production ou de récupérer après avoir effacé le volume de données. Vous n'avez pas besoin de réexécuter l'assistant ou de saisir à nouveau les informations d'identification Cloudflare.

## Après la restauration
- Ouvrez **Paramètres → Sauvegarde et restauration** pour confirmer le dernier horodatage du manifeste.
- Cochez **Agents → Présentation** pour vous assurer que les agents inscrits se reconnectent. Réémettez les clés d'agent si vous les avez alternées.
- Déclenchez une réconciliation si vous avez restauré dans un environnement différent (`Actions → Reconcile Now`).

Conservez des sauvegardes hors ligne régulières et associez-les au contrôle de version de votre pile de composition afin de pouvoir reconstruire rapidement l'intégralité du déploiement.
