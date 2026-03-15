# Interne vs externe `cloudflared`

DockFlare peut fonctionner selon deux modes pour gérer l'agent `cloudflared`, qui est le logiciel qui crée réellement la connexion persistante entre votre serveur et le réseau Cloudflare. Comprendre ces deux modes est essentiel pour choisir la configuration adaptée à votre environnement.

## Mode interne (par défaut)

En mode interne, DockFlare assume l'entière responsabilité de la gestion de l'agent `cloudflared`.

### Comment ça marche
Lorsque DockFlare démarre, il :
1. Créez un conteneur Docker dédié exécutant l'image `cloudflare/cloudflared`.
2. Configurez ce conteneur d'agent pour vous connecter à votre compte Cloudflare et utiliser le tunnel spécifié dans vos paramètres DockFlare.
3. Assurez-vous que l'agent est en cours d'exécution et redémarrez-le en cas d'échec.
4. Appliquez automatiquement tous les paramètres pertinents, tels que l'activation du point de terminaison des métriques Prometheus.

Il s'agit du mode **par défaut et recommandé** pour la plupart des utilisateurs.

### Avantages
* **Simplicité :** Il s'agit d'une configuration "sans configuration". DockFlare gère tout pour vous.
* **Compatibilité garantie :** DockFlare garantit que l'agent est configuré de manière à pouvoir fonctionner.
* **Gestion centralisée :** Tout ce qui concerne vos tunnels est géré par DockFlare.

### Inconvénients
* **Moins de contrôle :** Vous disposez d'un contrôle limité sur la configuration de l'agent `cloudflared` au-delà de ce qu'expose DockFlare.

---

## Mode `cloudflared` externe

En mode externe, vous êtes responsable de l'exécution et de la gestion de l'agent `cloudflared` vous-même. DockFlare se connectera à cet agent existant au lieu de créer le sien.

### Comment ça marche
DockFlare ne créera **pas** de conteneur `cloudflared`. Au lieu de cela, il supposera que vous disposez d’un agent `cloudflared` exécuté quelque part qu’il peut utiliser. Cela pourrait être :
* Un processus `cloudflared` s'exécutant directement sur le système d'exploitation hôte (par exemple, en tant que service `systemd`).
* Un conteneur `cloudflared` que vous gérez vous-même avec un fichier `docker-compose.yml` distinct ou une commande d'exécution Docker.
* Un agent `cloudflared` exécuté sur une machine entièrement différente.

Il s'agit d'un **mode avancé** destiné aux utilisateurs ayant des besoins spécifiques ou des configurations existantes complexes.

### Avantages
* **Contrôle maximal :** Vous avez un contrôle total sur l'agent `cloudflared`, y compris sa version, ses arguments de ligne de commande et son cycle de vie.
* **Intégration avec les configurations existantes :** Parfait si vous disposez déjà d'un agent `cloudflared` exécuté à d'autres fins.
* **Découplage :** Découple le cycle de vie de DockFlare du cycle de vie de l'agent `cloudflared`.

### Inconvénients
* **Complexité :** Vous êtes responsable de vous assurer que l'agent `cloudflared` est en cours d'exécution, configuré correctement et connecté au tunnel approprié.
* **Surcharge de configuration :** Vous devez configurer DockFlare pour utiliser cet agent externe.

### Comment activer le mode externe
Pour activer le mode externe, vous devez définir les variables d'environnement suivantes pour le conteneur DockFlare :

* `USE_EXTERNAL_CLOUDFLARED=true` : Ceci active le mode externe.
* `EXTERNAL_TUNNEL_ID` : il doit être défini sur l'UUID du tunnel que votre agent `cloudflared` externe est configuré pour utiliser.

Lorsque ces variables sont définies, DockFlare ignorera sa gestion d'agent interne et enverra à la place toutes les configurations de règles d'entrée au tunnel spécifié par `EXTERNAL_TUNNEL_ID`.