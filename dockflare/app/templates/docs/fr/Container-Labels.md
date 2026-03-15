# Référence des étiquettes de conteneurs

DockFlare est configuré principalement via les étiquettes Docker attachées à vos conteneurs. Cette page fournit une référence complète pour toutes les étiquettes prises en charge.

## Configuration de base

Ces étiquettes contrôlent la définition fondamentale du routage et du service pour un conteneur.

| Étiquette | Descriptif | Exemple |
| :--- | :--- | :--- |
| `dockflare.enable` | **Obligatoire.** L'interrupteur principal. Doit être défini sur `true` pour que DockFlare gère le conteneur. | `dockflare.enable=true` |
| `dockflare.hostname` | **Obligatoire.** Le nom d'hôte public de votre service. | `dockflare.hostname=myservice.example.com` |
| `dockflare.service` | **Obligatoire.** L'URL interne du service auquel Cloudflare Tunnel doit se connecter. Peut être `http`, `https`, `tcp`, `ssh`, `rdp`, `http_status:XXX` ou `bastion`. | `dockflare.service=http://my-app-container:8080` |
| `dockflare.path` | Le chemin de l'URL à acheminer vers ce service. Utile pour exposer plusieurs services sur le même nom d'hôte. | `dockflare.path=/api` |
| `dockflare.zonename` | (Facultatif) Zone Cloudflare explicite (domaine) où l'enregistrement DNS doit être créé. En cas d'omission, DockFlare détecte désormais automatiquement la zone en fonction du nom d'hôte et ne revient à la valeur par défaut configurée (`CF_ZONE_ID`) que lorsque la détection automatique échoue. | `dockflare.zonename=another-domain.com` |
| `dockflare.no_tls_verify` | S'il est défini sur `true`, désactive la vérification du certificat TLS pour la connexion entre `cloudflared` et votre service d'origine. Utile pour les origines avec des certificats auto-signés. | `dockflare.no_tls_verify=true` |
| `dockflare.originsrvname` | Définit un nom d'hôte SNI (Server Name Indication) spécifique pour la connexion TLS à l'origine. Ceci est également connu sous le nom de « Nom du serveur d'origine » dans le tableau de bord Cloudflare. | `dockflare.originsrvname=internal.service.local` |
| `dockflare.httpHostHeader` | Remplace l’en-tête `Host` envoyé depuis `cloudflared` à votre service d’origine. | `dockflare.httpHostHeader=custom-host.internal` |
| `dockflare.http2_origin` | S'il est défini sur `true`, active le protocole HTTP/2 pour la connexion entre `cloudflared` et votre service d'origine. Requis pour les services gRPC. S'applique uniquement aux services HTTP/HTTPS. | `dockflare.http2_origin=true` |
| `dockflare.disable_chunked_encoding` | S'il est défini sur `true`, désactive le codage de transfert fragmenté sur HTTP/1.1. Utile pour les serveurs WSGI (Flask, Django, FastAPI) et autres origines qui ne prennent pas correctement en charge les requêtes fragmentées. S'applique uniquement aux services HTTP/HTTPS. | `dockflare.disable_chunked_encoding=true` |

> **Conseil :** À partir de DockFlare v3.0, vous pouvez ignorer `dockflare.zonename` pour la plupart des charges de travail. Le maître détecte la zone Cloudflare correcte en faisant correspondre le suffixe du nom d'hôte et ne revient à la zone par défaut configurée que lorsqu'il ne trouve pas de correspondance. Fournissez l'étiquette lorsque vous souhaitez intentionnellement placer un enregistrement dans une zone différente.

> **Remarque :** L'option **Match SNI to Host** de Cloudflare est disponible dans la configuration manuelle des règles DockFlare dans le tableau de bord. Il n'est actuellement pas défini via une étiquette Docker.

---

## Configuration de la politique d'accès

Ces étiquettes vous permettent de créer et de gérer dynamiquement des applications Cloudflare Access pour sécuriser vos services.

**Remarque :** Il est fortement recommandé d'utiliser des **Groupes d'accès** (`dockflare.access.group`) pour gérer les stratégies. DockFlare 3.0.3 synchronise chaque groupe d'accès avec une politique d'accès Cloudflare réutilisable nommée, vous offrant ainsi une réutilisation un à plusieurs et des modifications bidirectionnelles. L’utilisation d’étiquettes individuelles est préférable pour les configurations uniques et uniques. Si `dockflare.access.group` ou `dockflare.access.groups` est utilisé, toutes les autres étiquettes `dockflare.access.*` sont ignorées.

### Modifications importantes dans la v3.0.3

#### Politique de contournement par défaut du système

À partir de la version 3.0.3, lorsque vous utilisez `dockflare.access.policy=bypass` ou `dockflare.access.group=bypass`, votre service fera référence à la stratégie réutilisable `public-default-bypass` gérée par le système au lieu de créer une stratégie en ligne. Cela permet de garder votre tableau de bord Cloudflare propre.

- **Avant la version 3.0.3 :** Chaque règle de contournement créait une stratégie en ligne distincte
- **v3.0.3+ :** Toutes les règles de contournement partagent une politique canonique `public-default-bypass`

#### Migration des anciennes étiquettes

DockFlare migre automatiquement les anciennes étiquettes de contournement pour utiliser la politique système centralisée :

- `dockflare.access.policy=bypass` → Utilise la stratégie système `public-default-bypass`
- `dockflare.access.group=bypass` → Utilise la stratégie système `public-default-bypass`

La migration s'effectue de manière transparente lors du traitement et de la réconciliation des conteneurs. Vos conteneurs continueront à fonctionner sans aucune modification requise.

#### Configuration d'accès simplifiée

Pour les scénarios d'accès complexes (authentification email/domaine, liste blanche IP, etc.), il est désormais recommandé de :

1. Créez un groupe d'accès sur la page **Politiques d'accès**
2. Référencez-le avec `dockflare.access.group=your-group-id`

Les options de création rapide ont été supprimées de l'interface utilisateur pour encourager ce flux de travail basé sur les meilleures pratiques.

#### Libellé de stratégie par défaut de zone

L'étiquette `dockflare.access.policy=default_tld` fonctionne toujours et héritera de la protection de la stratégie de caractère générique `*.domain.com` de votre zone. Si aucune politique de zone n’existe, le service sera public (pas d’application Access).

**Recommandation :** Créez des stratégies de zone par défaut pour tous vos domaines dans l'interface utilisateur pour une meilleure sécurité.

| Étiquette | Descriptif | Exemple |
| :--- | :--- | :--- |
| `dockflare.access.group` | L’ID d’un seul groupe d’accès préconfiguré à appliquer à ce service. L'ID peut être trouvé sur la page « Politiques d'accès » dans l'interface utilisateur de DockFlare. | `dockflare.access.group=internal-tools-policy` |
| `dockflare.access.groups` | Une liste d'ID de groupe d'accès à appliquer, séparés par des virgules. Cela vous permet de superposer plusieurs politiques sur un seul service. | `dockflare.access.groups=allow-team-a,allow-admins` |
| `dockflare.access.policy` | Type de stratégie principal. Peut être `bypass` (public), `authenticate` (connexion requise) ou `default_tld` (hérite d'une stratégie `*.domain.com`). S’il n’est pas défini, le service sera public. Préférez les groupes d’accès pour les politiques réutilisables ; ces étiquettes sont destinées aux remplacements spécialisés. | `dockflare.access.policy=authenticate` |
| `dockflare.access.name` | Un nom personnalisé pour l'application Cloudflare Access. La valeur par défaut est `DockFlare-{hostname}`. | `dockflare.access.name=My Web App Access` |
| `dockflare.access.session_duration` | La durée de la session pour les utilisateurs authentifiés (par exemple, `24h`, `30m`). La valeur par défaut est `24h`. | `dockflare.access.session_duration=1h` |
| `dockflare.access.app_launcher_visible` | Si `true`, rend l'application visible dans le lanceur d'applications Cloudflare Access. | `dockflare.access.app_launcher_visible=true` |
| `dockflare.access.allowed_idps` | Une liste d'UUID de fournisseur d'identité (IdP) autorisés, séparés par des virgules. Vous pouvez les trouver dans votre tableau de bord Cloudflare Zero Trust. | `dockflare.access.allowed_idps=uuid1,uuid2` |
| `dockflare.access.auto_redirect_to_identity` | Si `true`, les utilisateurs seront immédiatement redirigés vers la page de connexion de l'IdP au lieu de la page de démarrage de Cloudflare Access. | `dockflare.access.auto_redirect_to_identity=true` |
| `dockflare.access.custom_rules` | Une chaîne JSON représentant un tableau de règles de politique d'accès Cloudflare. Cela offre une flexibilité maximale pour les polices complexes et ponctuelles. | `dockflare.access.custom_rules='[{"email":{"email":"user@example.com"},"action":"allow"}]'` |

---

## Étiquettes indexées pour plusieurs domaines

DockFlare prend en charge la définition de plusieurs noms d'hôte pour un seul conteneur à l'aide d'étiquettes indexées. Ceci est utile pour exposer différents ports ou chemins du même service sur différents noms d'hôtes publics.

Pour utiliser des étiquettes indexées, préfixez l’étiquette avec un entier, en commençant par `0`.

* Un nom d'hôte indexé (`<index>.hostname`) est toujours requis.
* D'autres étiquettes au même index (par exemple, `<index>.service`, `<index>.path`) remplaceront les étiquettes de base (non indexées) pour ce nom d'hôte spécifique.
* Si une étiquette indexée n'est pas fournie, elle reviendra à la valeur de l'étiquette de base correspondante.

### Exemple

Cet exemple expose deux noms d'hôte à partir d'un seul conteneur :
1. `app.example.com` achemine vers l'interface web principale sur le port `80`.
2. `api.example.com` est acheminé vers l'API sur le port `3000` et est sécurisé avec un groupe d'accès spécifique.

```yaml
services:
  my-multi-service:
    image: my-app
    labels:
      - "dockflare.enable=true"

      # --- Definition 0 ---
      - "dockflare.0.hostname=app.example.com"
      - "dockflare.0.service=http://my-multi-service:80"

      # --- Definition 1 ---
      - "dockflare.1.hostname=api.example.com"
      - "dockflare.1.service=http://my-multi-service:3000"
      - "dockflare.1.access.group=api-access-policy"
```
