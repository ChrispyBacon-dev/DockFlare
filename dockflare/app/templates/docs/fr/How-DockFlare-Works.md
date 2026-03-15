# Comment fonctionne DockFlare

DockFlare sert de passerelle entre votre environnement Docker et le réseau Cloudflare, en automatisant l'exposition sécurisée de vos services sur Internet. Il surveille en continu votre hôte Docker et s'appuie sur l'API Cloudflare pour gérer les tunnels, les enregistrements DNS et les politiques d'accès en votre nom.

## Flux de travail principal

Le fonctionnement général peut être résumé en quelques étapes :

1. **Surveillance des événements Docker** : DockFlare écoute les événements du socket Docker, comme `start` et `stop` pour les conteneurs.

2. **Détection des labels** : lorsqu'un nouveau conteneur démarre, DockFlare vérifie la présence de labels `dockflare.`. S'il trouve `dockflare.enable=true`, il sait que ce conteneur doit être géré.

3. **Interaction avec l'API Cloudflare** : à partir de ces labels, DockFlare configure les ressources nécessaires dans Cloudflare :
   * **Cloudflare Tunnel** : DockFlare ajoute une règle d'ingress dans le tunnel Cloudflare désigné. Cette règle fait pointer le hostname public vers l'adresse réseau interne du conteneur, par exemple `http://my-app:8080`.
   * **Gestion DNS** : DockFlare crée un enregistrement CNAME dans votre zone DNS Cloudflare pour faire pointer le hostname public souhaité, par exemple `my-app.example.com`, vers le tunnel Cloudflare.
   * **Politiques d'accès** : si des labels de contrôle d'accès sont définis, DockFlare crée ou met à jour une politique Cloudflare Access réutilisable pour protéger le service avec des règles Zero Trust, par exemple en exigeant une connexion via un fournisseur d'identité ou en appliquant un `bypass` public.

4. **Nettoyage automatique** : lorsqu'un conteneur géré est arrêté ou supprimé, DockFlare lance automatiquement un processus de nettoyage. La règle d'ingress correspondante est retirée du tunnel Cloudflare et, si aucun autre service n'utilise encore ce hostname, DockFlare supprime aussi l'enregistrement DNS et l'application Access. Cela évite les entrées obsolètes et garde votre configuration Cloudflare propre.

## Composants en un coup d'œil

| Composant | Responsabilité |
| --- | --- |
| DockFlare Master | Héberge l'interface web et l'API, surveille les événements Docker et orchestre les tunnels Cloudflare, le DNS et les politiques d'accès. Il fonctionne sans privilèges root et communique avec Docker uniquement via le socket proxy. |
| Docker Socket Proxy | Sidecar `tecnativa/docker-socket-proxy` qui expose au Master la surface minimale de l'API Docker (`containers`, `events`, etc.). Il empêche le Master de monter directement le socket Docker brut. |
| Redis | Gère le cache, les files d'attente, le streaming des logs et le canal de heartbeat et de retour d'état des agents. Il s'exécute sur le réseau privé `dockflare-internal`. |
| DockFlare Agents (facultatif) | Processus distants qui reproduisent le comportement du Master sur d'autres hôtes, retransmettent les événements Docker et gèrent leur propre `cloudflared`. |
| `cloudflared` | Maintient la connexion du tunnel vers Cloudflare pour le Master ou pour chaque agent. |

## Modèle de configuration en couches

DockFlare utilise une approche de configuration souple et en couches, qui combine automatisation et contrôle fin :

1. **Labels Docker (couche de base)** : c'est la méthode principale et automatisée. Vous définissez directement dans `docker-compose.yml` ou dans votre commande `docker run` l'ensemble de la configuration du service : hostname, URL interne et politique d'accès. Ces labels constituent la source de vérité des services automatisés.

2. **Access Groups (couche d'abstraction)** : pour éviter de répéter des politiques d'accès complexes sur de nombreux services, vous pouvez créer des **Access Groups** réutilisables dans l'interface web. Ces modèles regroupent des règles comme « autoriser les e-mails de l'entreprise » ou « autoriser l'accès depuis certains pays », puis les synchronisent avec des politiques Cloudflare Access nommées et réutilisables. Le sélecteur `Public` ou `Authenticated` dans la fenêtre modale détermine si DockFlare émet une décision `bypass` ou `allow`. Vous pouvez ensuite appliquer toute une politique à un conteneur avec un simple label, par exemple `dockflare.access.group=my-policy-group`.

3. **Overrides dans l'interface web (couche de contrôle)** : l'interface web offre le niveau de contrôle le plus élevé. Depuis le tableau de bord, vous pouvez :
   * **remplacer** la politique d'accès d'un service, qu'elle ait été définie par des labels ou par un Access Group. Ces overrides sont persistants et ne sont pas perdus lors d'un redémarrage du conteneur.
   * **créer des règles d'ingress manuelles** pour des services qui ne tournent pas dans Docker, par exemple sur une autre machine du réseau.
   * **revenir** à la configuration définie dans les labels Docker d'un service et supprimer les overrides appliqués depuis l'interface.

Ce modèle en couches vous permet d'automatiser la plupart des services avec des labels Docker, tout en conservant la souplesse nécessaire pour gérer les exceptions et les scénarios plus complexes depuis l'interface web.

---

## Architecture des politiques d'accès (v3.0.3+)

### Système de politiques réutilisables

DockFlare utilise désormais une **architecture de politiques réutilisables**, alignée sur les bonnes pratiques de Cloudflare :

1. **Access Groups** → se synchronisent avec → **Cloudflare Reusable Policies**
2. **Access Applications** → référencent → **Reusable Policy IDs**
3. **Une source unique de vérité** → une mise à jour unique s'applique partout

Cette architecture élimine les doublons de politiques et permet de les gérer aussi bien depuis DockFlare que depuis le tableau de bord Cloudflare, avec synchronisation bidirectionnelle complète.

### Politiques gérées par le système

DockFlare gère automatiquement deux politiques principales pour garantir un comportement cohérent :

- **`public-default-bypass`** : politique de bypass pour l'accès public
  - Politique système non supprimable
  - Créée automatiquement lors de l'initialisation
  - Nom Cloudflare : `DockFlare-Default-Public-Access-Bypass`
  - Décision : `bypass` avec règle `everyone`
  - Utilisée par les services qui nécessitent un accès public sans protection de zone
  - Évite la duplication de politiques de bypass dans le tableau de bord Cloudflare

- **`authenticated-default`** : politique d'authentification par défaut
  - Politique système non supprimable
  - Créée automatiquement lors de l'initialisation
  - Nom Cloudflare : `DockFlare-Default-Authenticated-Access`
  - Décision : `allow` avec code PIN à usage unique et restriction d'adresse e-mail
  - Utilisée dans les scénarios de base d'accès authentifié

### Migration des anciens labels

DockFlare migre automatiquement les anciens labels vers les politiques système :

- `dockflare.access.policy=bypass` → utilise `public-default-bypass`
- `dockflare.access.group=bypass` → utilise `public-default-bypass`
- `dockflare.access.policy=authenticate` → utilise `authenticated-default`

La migration s'effectue de manière transparente lors du traitement et de la réconciliation des conteneurs. Aucune intervention manuelle n'est nécessaire.

### Politiques par défaut de zone

Les politiques wildcard au niveau de la zone (`*.domain.com`) apportent une sécurité en couches grâce à l'ordre de priorité :

1. **Politique spécifique à un hostname** (par exemple `app.example.com`) - priorité la plus élevée
2. **Politique wildcard de zone** (par exemple `*.example.com`) - repli
3. **Aucune politique** = accès public sans Access App - comportement par défaut

Ainsi, même les services oubliés ou non documentés restent protégés par la politique définie au niveau de la zone.

**Exemple :**
- Politique de zone : `*.internal.company.com` → impose une authentification avec une adresse e-mail d'entreprise
- Service spécifique : `public-demo.internal.company.com` → utilise `public-default-bypass`
- Service oublié : `test.internal.company.com` → reste protégé par la politique de zone et requiert une authentification
