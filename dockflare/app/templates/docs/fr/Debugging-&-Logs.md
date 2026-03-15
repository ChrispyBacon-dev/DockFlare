# Débogage et journaux

Lors du dépannage des problèmes avec DockFlare, vos principaux outils sont les journaux générés par le conteneur DockFlare et son agent `cloudflared` géré.

## 1. Vérification des journaux du conteneur DockFlare

La source d'informations la plus importante est la sortie du journal du conteneur DockFlare lui-même. Ces journaux fournissent une vue détaillée en temps réel de ce que fait DockFlare.

### Ce que vous trouverez dans les journaux :
* Détection des événements de démarrage/arrêt du conteneur Docker.
* Traitement des étiquettes `dockflare.*`.
* Appels effectués vers l'API Cloudflare.
* Messages de réussite ou réponses d'erreur détaillées de l'API Cloudflare.
* L'état des tâches en arrière-plan comme le nettoyage des ressources.

### Comment afficher les journaux :
Pour afficher les journaux, utilisez la commande Docker suivante dans votre terminal :
```bash
# View the full log history
docker logs dockflare

# Follow the logs in real-time
docker logs -f dockflare
```

## 2. Utilisation des journaux en temps réel de l'interface web

Pour plus de commodité, le tableau de bord DockFlare comprend une **visionneuse de journaux en temps réel** au bas de la page principale.

Cette visionneuse diffuse exactement les mêmes journaux que vous verriez avec `docker logs -f dockflare`, mais offre un moyen simple de voir ce qui se passe en ce moment sans quitter votre navigateur. Ceci est particulièrement utile pour observer les actions effectuées par DockFlare immédiatement après le démarrage ou l'arrêt d'un conteneur.

## 3. Vérification des journaux de l'agent `cloudflared`

Si vous pensez que le problème vient de la connexion entre votre serveur et le réseau Cloudflare, vous pouvez consulter directement les journaux du conteneur d'agent `cloudflared`.

### Comment afficher les journaux des agents :
Tout d’abord, vous devez trouver le nom du conteneur d’agent. Par défaut, il est nommé `cloudflared-agent-<tunnel-name>`, où `<tunnel-name>` est le nom du tunnel configuré dans vos paramètres DockFlare.

Vous pouvez trouver le nom exact avec `docker ps`.

Une fois que vous avez le nom, exécutez :
```bash
# Replace with the actual container name
docker logs cloudflared-agent-dockflare-tunnel
```

Ces journaux sont utiles pour diagnostiquer :
* Erreurs de connexion au Edge Cloudflare.
* Problèmes d'authentification avec votre jeton de tunnel.
* Erreurs au niveau du protocole pour le trafic proxy.

**Remarque :** Cela s'applique uniquement si vous utilisez le **Mode interne** par défaut. Si vous utilisez le [Mode externe](External-cloudflared-Mode.md), vous devrez vérifier les journaux de votre propre processus d'agent `cloudflared`.

## 4. Vérification du tableau de bord Cloudflare

Enfin, n'oubliez pas d'utiliser le tableau de bord Cloudflare comme outil de débogage.
* **Page DNS :** Vérifiez si les enregistrements CNAME ont été créés comme prévu.
* **Zero Trust Dashboard :** Accédez à **Accès -> Tunnels** pour vérifier l'état de votre tunnel et ses règles d'entrée.
* **Tableau de bord Zero Trust :** Accédez à **Accès -> Applications** pour vérifier la configuration et l'état de vos politiques Zero Trust. Le statut « Dernière vue » sur les politiques peut être très informatif.
