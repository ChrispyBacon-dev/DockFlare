# Meilleures pratiques et exemples de politiques d'accès

La fonctionnalité de sécurité la plus puissante de DockFlare est constituée par les **Groupes d'accès**. Ils offrent un moyen centralisé, réutilisable et maintenable de sécuriser vos services à l'aide de Cloudflare Zero Trust.

## La « règle d'or » : utiliser les groupes d'accès

La meilleure pratique la plus importante consiste à **utiliser les groupes d'accès pour toutes vos stratégies d'accès communes**.

Les groupes d'accès sont des modèles de stratégie que vous créez dans l'interface utilisateur web de DockFlare. Au lieu de définir des règles complexes avec plusieurs étiquettes sur chaque conteneur, vous créez une stratégie une seule fois et l'appliquez avec une seule étiquette claire. DockFlare v3.0.3 synchronise désormais chaque groupe avec une politique d'accès Cloudflare réutilisable afin qu'un même ensemble de décisions puisse servir plusieurs applications.

---

## Comment créer et utiliser des groupes d'accès

La création d'un groupe d'accès est un processus simple qui se déroule entièrement dans l'interface DockFlare.

### Étape 1 : Créer le groupe d'accès

1. Accédez à la page **Politiques d'accès** à partir de la barre de navigation principale de l'interface utilisateur DockFlare.
2. Cliquez sur le bouton **"Ajouter un groupe d'accès"**.
3. Donnez à votre groupe un **identifiant unique et descriptif**. Cet identifiant est ce que vous utiliserez dans vos étiquettes Docker. Par exemple : `admin-users`, `home-network`, `geo-block`.
4. Choisissez le **Mode d'accès** dans les onglets en haut du modal :
    * **Authentifié** nécessite que les utilisateurs se connectent et émet une décision `allow`.
    * **Public** utilise une décision `bypass` afin que l'application reste ouverte tout en respectant les filtres géographiques.
5. Remplissez les entrées qui apparaissent pour le mode sélectionné (e-mails pour Authentifié, liste de pays facultative pour les deux).
6. Ajustez les paramètres facultatifs tels que la durée de la session, la visibilité du lanceur d'application et la redirection automatique de l'IdP si vous êtes en mode authentifié.
7. Enregistrez le groupe. DockFlare écrit la définition localement et la synchronise avec Cloudflare sous le nom `DockFlare-AccessGroup-<id>`.

### Étape 2 : Appliquer le groupe d'accès

Une fois créé, vous disposez de deux manières d’appliquer votre groupe d’accès à un service :

#### A) Avec une étiquette Docker (la méthode recommandée)

Pour tout conteneur nouveau ou existant, ajoutez simplement l'étiquette `dockflare.access.group` avec l'ID du groupe que vous avez créé.

```yaml
services:
  grafana:
    image: grafana/grafana
    labels:
      - "dockflare.enable=true"
      - "dockflare.hostname=monitoring.example.com"
      - "dockflare.service=http://grafana:3000"
      # Apply the entire policy with one simple label:
      - "dockflare.access.group=admin-users"
```
Vous pouvez également appliquer plusieurs groupes en utilisant `dockflare.access.groups` avec une liste d'ID séparés par des virgules :
`dockflare.access.groups=admin-users,home-network`

#### Politiques gérées par le système

DockFlare fournit deux politiques système intégrées qui sont automatiquement disponibles :

- **`public-default-bypass`** - Accès public avec décision de contournement (utilisation pour des services véritablement publics)
- **`authenticated-default`** - Authentification par défaut avec code PIN à usage unique + restriction de courrier électronique

Ces stratégies système ne peuvent pas être supprimées et servent de base à la protection des zones et à la migration des étiquettes héritées.

#### B) Via l'interface web (pour les règles manuelles ou les remplacements)

Vous pouvez également appliquer un groupe d'accès à n'importe quelle règle directement depuis le tableau de bord :
1. Recherchez la règle d'entrée que vous souhaitez modifier sur le tableau de bord principal.
2. Cliquez sur le bouton **"Gérer la règle"**.
3. Dans le mode d'édition, sélectionnez le(s) groupe(s) d'accès souhaité(s) dans le menu déroulant « Groupes d'accès ».
4. Enregistrez les modifications.

C'est parfait pour appliquer des politiques à des règles créées manuellement (pour les services non Docker) ou pour remplacer temporairement une politique définie par les étiquettes Docker.

---

## Exemples de politiques

Voici quelques configurations de stratégie courantes que vous pouvez créer au sein d’un groupe d’accès.

### Exemple 1 : Authentification par e-mail

Il s'agit du cas d'utilisation le plus courant : autoriser uniquement des utilisateurs spécifiques pouvant s'authentifier auprès de votre fournisseur d'identité configuré (par exemple, Google, GitHub ou un code PIN à usage unique envoyé à leur adresse e-mail).

* **ID de groupe :** `admin-users`
* **Mode :** *Authentifié*
* **E-mails autorisés :** `user1@example.com`, `user2@example.com`
* **Durée de la session :** `24h`

DockFlare crée une politique réutilisable avec une décision `allow` pour les e-mails répertoriés et une règle de transition `deny` pour tous les autres. Appliquez le groupe avec `dockflare.access.group=admin-users`.

### Exemple 2 : Autoriser l'adresse IP de votre domicile

Cette politique restreint l'accès à votre réseau domestique, vous permettant d'ignorer l'invite de connexion lorsque vous êtes sur une adresse IP de confiance tout en appliquant l'authentification ailleurs.

1. **Trouvez votre adresse IP publique :** Dans votre navigateur, recherchez « quelle est mon adresse IP ». Votre adresse IP publique sera affichée (par exemple, `203.0.113.55`).
2. **Créez le groupe d'accès :**
    * **ID de groupe :** `home-network`
    * **Mode :** *Authentifié*
    * **E-mails autorisés :** `you@example.com`
    * **Contourner les adresses IP :** ajoutez `203.0.113.55/32` au champ de la liste autorisée des adresses IP.

DockFlare génère une politique qui contourne d'abord votre plage IP, puis exige que les e-mails répertoriés s'authentifient. Tous les autres reçoivent une décision de refus.

### Exemple 3 : Géo-clôture (blocage de plusieurs pays)

Cette politique maintient votre site marketing public tout en limitant le trafic en provenance de régions spécifiques.

* **ID de groupe :** `public-eu`
* **Mode :** *Public*
* **Pays bloqués :** `RU`, `CN`, `KP`

La politique réutilisable qui en résulte émet une décision Cloudflare `bypass` pour tout le monde, à l'exclusion des pays répertoriés. Combinez-le avec d'autres groupes si vous devez superposer des contrôles supplémentaires (`dockflare.access.groups=public-eu,admin-users`).

---

## Politiques par défaut de zone – Meilleures pratiques de sécurité

### Que sont les politiques par défaut de zone ?

Les politiques par défaut de zone sont des applications d'accès génériques `*.domain.com` qui protègent TOUS les sous-domaines d'une zone DNS, y compris ceux que vous n'avez pas encore explicitement configurés.

### Pourquoi vous en avez besoin

**Le problème :** Si vous oubliez d'ajouter une stratégie d'accès à un service, celle-ci est exposée publiquement par défaut.

**La solution :** Une stratégie générique au niveau de la zone agit comme un filet de sécurité. Même si vous oubliez de configurer `forgotten-service.yourdomain.com`, la stratégie `*.yourdomain.com` continuera à le couvrir.

### Comment les configurer

1. Accédez à la page **Politiques d'accès**.
2. Faites défiler jusqu'à la section **Politiques de zone par défaut (*.tld Wildcards)**
3. Recherchez les zones avec le badge « Non protégé » ⚠️
4. Cliquez sur **Créer une stratégie**
5. Sélectionnez le groupe d'accès approprié :
   - **Pour les domaines publics :** Utilisez `public-default-bypass`
   - **Pour les domaines internes :** Utilisez une politique d'authentification
   - **Pour un usage mixte :** Utilisez votre politique la plus restrictive

### Bonnes pratiques

- ✅ **Toujours créer des politiques de zone** pour les domaines de production
- ✅ **Utiliser des politiques d'authentification** pour les zones internes/privées
- ✅ **Utilisez le contournement public** uniquement pour les zones véritablement publiques
- ✅ **Révisez régulièrement** - vérifiez mensuellement l'état de protection de la zone
- ⚠️ **Mémoriser la priorité** - Les politiques de nom d'hôte spécifiques remplacent les politiques de caractères génériques

### Ordre de priorité des règles

Cloudflare évalue les politiques d'accès dans cet ordre :

1. **Correspondance exacte du nom d'hôte** (par exemple, `app.example.com`) - Priorité la plus élevée
2. **Correspondance générique** (par exemple, `*.example.com`) – Repli
3. **Aucune correspondance** = Accès public (pas d'application Access) - Par défaut

Cela signifie que vous pouvez avoir une politique par défaut de zone restrictive tout en créant des exceptions spécifiques pour des services individuels.

---

## Gestion des politiques Cloudflare externes

### Comprendre les types de politiques

DockFlare affiche trois types de politiques dans la page Politiques d'accès, chacune avec un badge visuel :

- **🟦 DockFlare** - Politiques créées et gérées par DockFlare (préfixe : `DockFlare-`)
- **🟪 Externe** - Politiques créées en dehors de DockFlare (outils manuels ou autres)
- **🟧 Système** - Politiques système non supprimables (`public-default-bypass`, `authenticated-default`)

### Synchronisation des politiques externes

Par défaut, DockFlare importe uniquement les stratégies avec le préfixe `DockFlare-`. Cela permet de garder votre liste de politiques propre et axée sur l'infrastructure des conteneurs.

**Pour synchroniser TOUTES les politiques Cloudflare** (y compris celles créées manuellement) :

1. Définissez la variable d'environnement : `SYNC_ALL_CLOUDFLARE_POLICIES=true`
2. Redémarrez DockFlare
3. Cliquez sur **"Synchroniser depuis Cloudflare"** sur la page Politiques d'accès.

Les politiques externes apparaîtront avec un badge violet **"Externe"**.

### Pourquoi importer des politiques externes ?

**Avantages :**
- Visibilité complète de l'ensemble de votre configuration Cloudflare Access
- Réutiliser les politiques existantes sans les recréer
- Gestion centralisée dans une seule interface
- Appliquer n'importe quelle politique à n'importe quel service (géré par DockFlare ou non)

**Inconvénients :**
- Liste de politiques plus longue si vous avez de nombreuses politiques externes
- Risque de modifier accidentellement les politiques utilisées par les services non-DockFlare

### Organiser vos politiques

**Conseil :** Renommez les stratégies externes dans Cloudflare pour utiliser le préfixe `DockFlare-`

Vous pouvez organiser des politiques externes en les renommant dans le tableau de bord Cloudflare :

1. Ouvrez la stratégie dans **Cloudflare Zero Trust**
2. Renommez-le pour utiliser le préfixe `DockFlare-` (par exemple, `DockFlare-LegacyVPN` ou `DockFlare-ThirdPartyApp`)
3. Cliquez sur **"Synchroniser depuis Cloudflare"** dans DockFlare
4. La politique apparaît désormais comme une politique **gérée par DockFlare** (badge bleu)

Cela vous permet de :
- ✅ Regroupez toutes les politiques visibles sur DockFlare avec une dénomination cohérente
- ✅ Filtrer et trier les politiques par type
- ✅ Distinguer « géré par DockFlare » de « juste visible dans DockFlare »

### Politiques de filtrage

Utilisez le menu déroulant **Filtre** pour afficher des types de règles spécifiques :

- **Toutes les politiques** - Affiche tout (DockFlare, Externe, Système)
- **DockFlare-Managed** - Affiche uniquement les politiques portant un badge bleu
- **Externe** – Affiche uniquement les politiques portant un badge violet
- **Système** - Affiche uniquement les stratégies système

### Caractéristiques de sécurité

**Protection de la politique externe :**

Lors de la suppression ou de la modification de politiques externes, DockFlare affiche un avertissement :

> ⚠️ AVERTISSEMENT : Il s'agit d'une politique EXTERNE non créée par DockFlare.
>
> La modification de cette politique peut affecter les services en dehors de DockFlare.
>
> Etes-vous absolument sûr ?

Cela évite les modifications accidentelles des politiques gérées par d’autres outils ou configurations manuelles.

### Bonnes pratiques

1. **Configuration par défaut (recommandée) :**
   - Conserver `SYNC_ALL_CLOUDFLARE_POLICIES=false` (par défaut)
   - Seules les politiques gérées par DockFlare apparaissent
   - Liste de politiques claire et ciblée

2. **Configuration avancée (utilisateurs expérimentés) :**
   - Activer `SYNC_ALL_CLOUDFLARE_POLICIES=true`
   - Afficher et gérer TOUTES les politiques en un seul endroit
   - Renommez les politiques externes en préfixe `DockFlare-` pour l'organisation.

3. **Approche hybride :**
   - Garder la synchronisation désactivée par défaut
   - Renommez manuellement les politiques externes importantes en `DockFlare-*` dans Cloudflare
   - Ils apparaîtront automatiquement après la prochaine synchronisation

4. **Convention de dénomination des politiques :**
   ```
   DockFlare-AccessGroup-<id>     # Auto-generated by access groups
   DockFlare-<custom-name>         # Your renamed external policies
   <anything-else>                 # Pure external (only visible if sync enabled)
   ```
