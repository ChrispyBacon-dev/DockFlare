# Utilisation de l'interface web

L'interface web de DockFlare est un outil puissant pour gérer, surveiller et configurer vos services. Elle offre un cadre clair pour les tâches qui vont au-delà de la simple configuration par labels Docker.

## Le tableau de bord (page principale)

La première page que vous voyez après la connexion est le tableau de bord principal. C'est l'endroit central pour suivre l'état de tous vos services gérés.

* **Tableau des règles d'entrée gérées :** Ce tableau répertorie toutes les règles d'entrée gérées par DockFlare, qu'elles proviennent d'un conteneur Docker ou qu'elles aient été créées manuellement.
    * **Nom d'hôte :** Le nom d'hôte public du service.
    * **Service :** L'URL de destination interne.
    * **Source :** Indique si la règle provient de `Docker` ou si elle a été créée manuellement dans l'interface.
    * **Statut :** Indique si la règle est `active`, `pending_deletion` ou si elle a un `UI Override`.
    * **Accès :** Affiche le groupe d'accès et le badge de mode appliqués. Lors de la synchronisation des politiques réutilisables, vous pouvez aussi voir des indicateurs comme `Public` ou `Authenticated`, les noms de groupes correspondants et des liens rapides vers le tableau de bord Cloudflare.
    * **Gérer la règle :** Ce bouton vous permet de modifier n'importe quelle règle.
* **Journaux en temps réel :** Sous le tableau, vous trouverez une visionneuse qui affiche en temps réel les journaux du backend DockFlare, ce qui est très utile pour le débogage.

## Gestion des règles

L'interface utilisateur vous donne un contrôle total sur vos règles d'entrée.

* **Ajouter une règle manuelle :** Le bouton "Ajouter une règle manuelle" vous permet de créer des règles d'entrée pour les services qui ne s'exécutent pas dans Docker (par exemple, un service sur une autre machine de votre réseau local). Le formulaire vous permet de spécifier le nom d'hôte, l'URL du service et éventuellement d'appliquer un groupe d'accès.
* **Modifier n'importe quelle règle :** Le bouton « Gérer la règle » à côté de chaque règle ouvre une fenêtre modale dans laquelle vous pouvez modifier sa configuration. C'est aussi là que vous pouvez appliquer un `UI Override` à une règle initialement créée à partir d'étiquettes Docker.
* **Revenir aux étiquettes :** Si une règle Docker a un `UI Override`, un bouton « Revenir aux étiquettes » apparaît. Il vous permet d'annuler les modifications manuelles et de rendre à nouveau la règle pilotée par ses étiquettes Docker.

## Page des politiques d'accès

Cette page constitue l'emplacement central pour gérer vos **groupes d'accès** réutilisables et sécuriser vos zones DNS avec des stratégies de caractères génériques.

### Politiques d'accès avancées

Depuis la section Groupes d'accès, vous pouvez :
* **Créez** de nouveaux groupes d'accès à l'aide du modal à deux onglets (Authentifié vs Public). Les bannières de guidage sont mises à jour par onglet afin que vous compreniez quand DockFlare émettra une décision Cloudflare `allow` ou `bypass`.
* **Modifier** les groupes d'accès existants. Le modal applique la validation spécifique au mode (e-mails requis pour l'authentification) et maintient les paramètres géographiques/IP visibles pour les deux modes.
* **Supprimer** les groupes d'accès qui ne sont plus utilisés (les stratégies système telles que `public-default-bypass` ne peuvent pas être supprimées).
* **Synchronisez depuis Cloudflare** pour importer les politiques réutilisables DockFlare existantes depuis votre compte.
* Utilisez le menu d'action à côté de chaque entrée pour ouvrir la politique correspondante directement dans le tableau de bord Cloudflare via le raccourci de l'icône Cloudflare.

**Remarque :** La stratégie système `public-default-bypass` est automatiquement créée et gérée par DockFlare. Tous les services utilisant l'accès « Contourner » font référence à cette politique unique, gardant ainsi votre tableau de bord Cloudflare propre.

### Politiques par défaut de zone (caractères génériques *.tld)

La deuxième section présente les **Politiques de zone par défaut** : une fonctionnalité de bonnes pratiques de sécurité qui protège tous les sous-domaines :

* **Statut de protection :** Les badges visuels indiquent quelles zones DNS ont des politiques génériques `*.domain.com` (Protégées 🛡️) et lesquelles n'en ont pas (Non protégées ⚠️).
* **Créer une stratégie de zone :** Cliquez sur « Créer une stratégie » sur n'importe quelle zone non protégée pour créer une application d'accès générique.
* **Sélectionnez la stratégie :** Choisissez quel groupe d'accès doit protéger tous les sous-domaines de la zone (il peut s'agir d'un contournement public, d'une authentification ou de toute stratégie personnalisée).
* **Filet de sécurité :** Même si vous oubliez d'ajouter une stratégie à un service spécifique, la stratégie générique au niveau de la zone continuera à le protéger.

**Bonne pratique :** Créez des stratégies de zone par défaut pour tous vos domaines. Pour les domaines publics, utilisez la stratégie de contournement par défaut. Pour les domaines internes/privés, utilisez une politique d'authentification. Cela garantit qu’aucun sous-domaine n’est accidentellement exposé.

Pour plus de détails, consultez le guide [Bonnes pratiques et exemples de politiques d'accès](Access-Policy-Best-Practices.md).

## Page de paramètres

La page Paramètres contient diverses options d'administration et de configuration :

* **Tunnels Cloudflare :** Cette section répertorie tous les tunnels Cloudflare trouvés sur votre compte, leur statut et leurs agents `cloudflared` connectés. Vous pouvez également afficher tous les enregistrements DNS CNAME pointant vers l'un de vos tunnels.
* **Sauvegarde et restauration :** Téléchargez une archive de sauvegarde DockFlare complète (`.zip`) contenant la configuration chiffrée, les clés d'agent et l'état, ou téléchargez une archive précédemment exportée pour restaurer l'instance.
* **Sécurité :**
    * **Modifier le mot de passe :** Modifiez votre mot de passe pour l'interface utilisateur web.
    * **Désactiver la connexion par mot de passe :** Pour les cas d'utilisation avancés où vous placez DockFlare derrière un autre proxy d'authentification. **⚠️ Avertissement :** Cela crée un risque de sécurité en raison de l'exposition du réseau Docker : n'importe quel conteneur sur le même réseau Docker peut contourner l'authentification externe et accéder directement à l'API de DockFlare. Nous vous recommandons fortement d'utiliser plutôt les fournisseurs OAuth/OIDC pour faciliter l'authentification unique sans sacrifier la sécurité. Voir [Accès à l'interface web](Accessing-the-Web-UI.md) pour connaître toutes les implications en matière de sécurité.
* **Informations d'identification Cloudflare :** Vous permet de mettre à jour votre identifiant de compte Cloudflare et votre jeton API après la configuration initiale.
* **Configuration principale :** Vous permet de modifier des paramètres tels que le nom du tunnel et le délai de grâce des règles.
