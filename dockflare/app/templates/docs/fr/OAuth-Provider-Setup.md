## Configuration du fournisseur OAuth

> **📌 Important :** Ce guide sert à configurer **l'authentification de l'interface web de DockFlare**. Si vous souhaitez configurer OAuth/OIDC pour les **politiques d'accès Cloudflare** afin de protéger vos services, consultez plutôt [Fournisseurs d'identité](Identity-Providers.md).

DockFlare permet de déléguer l'authentification des utilisateurs à des fournisseurs externes via le standard OpenID Connect (OIDC). Cela permet de mettre en place le single sign-on (SSO) pour l'interface web de DockFlare et de l'intégrer à des fournisseurs d'identité comme Google, Authentik, Okta et d'autres.

### Ajouter un nouveau fournisseur

Suivez les étapes suivantes pour ajouter un fournisseur OIDC :

1. **Ouvrez les paramètres :** depuis le tableau de bord principal, accédez à la page **Paramètres**.
2. **Repérez la section OAuth :** faites défiler jusqu'à **Authentification OAuth**.
3. **Ajoutez un fournisseur :** cliquez sur **Ajouter un fournisseur** pour ouvrir le formulaire de configuration.

Les champs suivants sont disponibles :

* **Type de fournisseur :** ce champ est défini sur `OpenID Connect (OIDC)`, le standard moderne d'authentification fédérée.
* **URL de l'émetteur :** c'est le champ le plus important. Il s'agit de l'URL de base de votre fournisseur OIDC, que DockFlare utilise pour découvrir automatiquement sa configuration. Par exemple : `https://accounts.google.com` ou `https://authentik.yourdomain.com/application/o/dockflare/`.
* **ID du fournisseur :** nom court, unique et en minuscules pour ce fournisseur, par exemple `google` ou `authentik-corp`. Cet identifiant est utilisé en interne et dans l'URL de rappel.
* **Nom d'affichage :** nom affiché sur le bouton de connexion, par exemple `Google` ou `Corporate SSO`.
* **ID client :** identifiant public de l'application DockFlare, fourni par la console développeur de votre fournisseur OIDC.
* **Secret client :** secret confidentiel de l'application DockFlare, également fourni par la console du fournisseur.
* **Activer le fournisseur :** cette case permet d'activer ou de désactiver le fournisseur à tout moment.

Une fois les champs remplis, cliquez sur **Ajouter un fournisseur** pour enregistrer la configuration.

### Trouver votre URL de rappel

Après avoir ajouté un fournisseur, l'**URL de rappel** requise, également appelée « URI de redirection autorisé », s'affiche sous l'entrée du fournisseur sur la page Paramètres.

Vous devez copier exactement cette URL et l'ajouter à la liste des URL de rappel autorisées dans la console d'administration de votre fournisseur.

---

### Exemple : configurer Google

Voici un exemple rapide pour configurer Google comme fournisseur OAuth.

1. **Accédez à Google Cloud Console :** ouvrez la page [API et services > Identifiants](https://console.cloud.google.com/apis/credentials).
2. **Créez les identifiants :** cliquez sur **+ CRÉER DES IDENTIFIANTS** puis sélectionnez **ID client OAuth**.
3. **Configurez l'application :**
   * Définissez **Type d'application** sur **Application Web**.
   * Donnez-lui un nom, par exemple `DockFlare`.
4. **Ajoutez un URI de redirection :**
   * Sous **URI de redirection autorisés**, cliquez sur **+ AJOUTER URI**.
   * Saisissez l'URL de rappel fournie par DockFlare. Elle ressemblera à ceci : `https://your-dockflare-domain.com/auth/google/callback`.
5. **Créez et copiez :** cliquez sur **CRÉER**. Une fenêtre s'ouvrira avec votre **ID client** et votre **secret client**. Copiez ces valeurs.
6. **Configurez DockFlare :**
   * **URL de l'émetteur :** `https://accounts.google.com`
   * **ID du fournisseur :** `google`
   * **Nom d'affichage :** `Google`
   * **ID client :** `(Your Client ID from Google)`
   * **Secret client :** `(Your Client Secret from Google)`

Enregistrez le fournisseur dans DockFlare. Vous pourrez ensuite vous connecter avec votre compte Google.

---

### Configurer DockFlare avec OAuth et les politiques d'accès

Lorsque vous utilisez l'authentification OAuth, vous pouvez vouloir protéger l'interface principale de DockFlare avec des politiques d'accès, tout en veillant à ce que les callbacks OAuth continuent de fonctionner correctement. C'est particulièrement important si votre instance DockFlare est protégée par des restrictions IP ou d'autres contrôles d'accès.

#### **Bonne pratique : utiliser une politique de bypass pour les callbacks OAuth**

Utilisez des labels indexés pour créer des règles distinctes pour l'interface principale et pour les chemins de callback OAuth :

```yaml
services:
  dockflare:
    image: alplat/dockflare:stable
    labels:
      # Main DockFlare interface with access policy
      - "dockflare.enable=true"
      - "dockflare.hostname=dockflare.example.com"
      - "dockflare.service=http://dockflare:5000"
      - "dockflare.access.group=team"  # your custom access policy

      # OAuth callback paths with bypass policy (required for OAuth to work)
      - "dockflare.0.hostname=dockflare.example.com"
      - "dockflare.0.path=/auth/google/callback"
      - "dockflare.0.service=http://dockflare:5000"
      - "dockflare.0.access.policy=bypass"

      # Add additional callback paths for other providers if needed
      - "dockflare.1.hostname=dockflare.example.com"
      - "dockflare.1.path=/auth/github/callback"
      - "dockflare.1.service=http://dockflare:5000"
      - "dockflare.1.access.policy=bypass"
```

#### **Pourquoi cette configuration est nécessaire**

- **Protection de l'interface principale :** votre tableau de bord DockFlare reste protégé par la politique d'accès choisie.
- **Fonctionnement d'OAuth :** les callbacks OAuth peuvent atteindre DockFlare sans être bloqués par une barrière d'authentification.
- **Sécurité :** seuls les chemins de callback spécifiques sont contournés, pas l'application entière.
- **Flexibilité :** fonctionne avec n'importe quelle combinaison de politiques d'accès, qu'elles soient basées sur l'IP, l'authentification ou autre.

#### **Remarques importantes**

1. **Correspondance exacte du chemin :** le chemin de callback doit correspondre exactement à celui attendu par votre fournisseur OAuth.
2. **Plusieurs fournisseurs :** ajoutez une règle indexée distincte pour chaque fournisseur OAuth configuré.
3. **Pas de jokers :** évitez les chemins génériques pour des raisons de sécurité ; utilisez des URL de callback précises.
4. **Tests :** une fois la configuration terminée, testez à la fois l'accès protégé à l'interface principale et les flux de connexion OAuth.
