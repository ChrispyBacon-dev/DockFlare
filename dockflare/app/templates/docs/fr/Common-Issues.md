# Problèmes courants

Cette page répertorie certains des problèmes courants que les utilisateurs peuvent rencontrer et comment les résoudre.

---

### Problème : le conteneur DockFlare ne parvient pas à démarrer ou est dans une boucle de redémarrage.

**Solution :**
1. **Vérifiez les journaux Docker :** La première étape consiste toujours à vérifier les journaux du conteneur DockFlare. Exécutez la commande suivante :
    ```bash
    docker logs dockflare
    ```
2. **Rechercher les erreurs :** Recherchez les messages d'erreur. Les causes courantes incluent :
    * Un fichier `docker-compose.yml` non valide (par exemple, syntaxe incorrecte, problèmes de montage de volume).
    * Problèmes avec le démon Docker lui-même.
    * Problèmes de connectivité ou d'autorisation avec le service docker-socket-proxy ou le paramètre `DOCKER_HOST`.

---

### Problème : les enregistrements DNS ne sont pas créés dans Cloudflare.

**Solution :**
1. **Vérifiez les journaux DockFlare :** Recherchez les messages d'erreur liés à l'API Cloudflare. Les journaux vous indiqueront souvent exactement pourquoi l'appel API a échoué.
2. **Vérifiez les autorisations des jetons API :** Il s'agit de la cause la plus courante. Assurez-vous que votre jeton API Cloudflare dispose des autorisations requises. Au minimum, il vous faut :
    * `Zone:DNS:Edit` pour chaque zone que vous souhaitez que DockFlare gère.
    * `Zone:Zone:Read`
3. **Vérifier la configuration des zones :**
    * Assurez-vous que l'**ID de zone** que vous avez fourni lors de la configuration est correct.
    * Si vous utilisez l'étiquette `dockflare.zonename`, vérifiez que le nom de la zone est correctement orthographié.

---

### Problème : Une stratégie d'accès (Zero Trust) n'est pas appliquée à un service.

**Solution :**
1. **Vérifiez les autorisations du jeton API :** Assurez-vous que votre jeton API dispose de l'autorisation `Account:Access: Apps and Policies:Edit`.
2. **Vérifiez les remplacements de l'interface utilisateur :** Dans le tableau de bord DockFlare, vérifiez si la règle a un statut « Remplacement de l'interface utilisateur ». Les remplacements de l'interface utilisateur ont priorité sur les étiquettes.
3. **Vérifiez l'ID du groupe d'accès :** Si vous utilisez `dockflare.access.group`, assurez-vous que l'ID que vous avez spécifié dans l'étiquette **exactement** correspond à l'ID que vous avez créé pour le groupe d'accès sur la page "Politiques d'accès".
4. **Vérifiez le tableau de bord Cloudflare :** Connectez-vous à votre tableau de bord Cloudflare Zero Trust. Accédez à **Access -> Applications** pour voir si l'application Access a été créée. Parfois, Cloudflare affichera une erreur qui n'est pas visible dans la réponse de l'API.

---

### Problème : j'obtiens une erreur `ERR_TOO_MANY_REDIRECTS` lorsque j'essaie d'accéder à mon service.

**Solution :**
Cette erreur se produit presque toujours en raison d'une mauvaise configuration des paramètres SSL/TLS entre votre service d'origine et Cloudflare.

1. **Vérifiez le mode SSL/TLS de Cloudflare :** Dans votre tableau de bord Cloudflare, accédez aux paramètres SSL/TLS de votre domaine. Assurez-vous que votre mode de cryptage est défini sur **Complet (Strict)**.
2. **Évitez les doubles redirections :** Le mode SSL « flexible » dans Cloudflare peut provoquer ce problème si votre application backend tente également de rediriger de HTTP vers HTTPS. Le navigateur reste bloqué dans une boucle.
3. **Utilisez `https` dans l'URL de votre service :** Si votre service backend prend en charge HTTPS, utilisez `https://` dans votre étiquette `dockflare.service` (par exemple, `dockflare.service=https://my-app:443`). Cela garantit que la connexion de `cloudflared` à votre service est également cryptée.

---

### Problème : Un service derrière Traefik/Proxmox ne fonctionne que lorsque "Match SNI to Host" de Cloudflare est activé.

**Solution :**
1. Modifiez la règle manuelle dans DockFlare et activez **Match SNI to Host**.
2. Enregistrez la règle et vérifiez l'itinéraire dans Cloudflare Zero Trust.
3. Si vous avez également besoin que DockFlare conserve les champs de route côté Cloudflare que DockFlare ne modélise pas, accédez à **Paramètres → Paramètres généraux** et activez **Conserver les champs d'entrée Cloudflare non gérés**.

---

### Problème : le conteneur `cloudflared-agent` géré ne parvient pas à démarrer avec une erreur « réseau obsolète ».

**Solution :**
Cela peut se produire si le réseau Docker utilisé par l'agent a été supprimé et recréé. DockFlare est conçu pour gérer cela automatiquement.

1. **Redémarrez DockFlare :** Un simple redémarrage du conteneur DockFlare (`docker compose restart dockflare`) devrait résoudre ce problème.
2. **Comment ça marche :** Au démarrage, DockFlare vérifie la santé de son agent géré. S'il détecte ce problème spécifique, il supprimera automatiquement le conteneur d'agent défectueux et en créera un nouveau avec la configuration correcte. Il s'agissait d'un bug spécifique corrigé dans la version `v1.9.5`. Assurez-vous que vous utilisez une version récente de DockFlare.