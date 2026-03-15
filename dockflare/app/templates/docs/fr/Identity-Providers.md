# Fournisseurs d'identité

> **📌 Important :** Ce guide explique comment configurer des **fournisseurs d'identité pour les politiques d'accès Cloudflare** afin de protéger vos services et applications. Si vous souhaitez configurer OAuth/OIDC pour **la connexion à l'interface web de DockFlare**, consultez plutôt [Configuration du fournisseur OAuth](OAuth-Provider-Setup.md).

Les fournisseurs d'identité (IdP) permettent d'activer l'authentification OAuth/OIDC pour vos applications protégées par Cloudflare Zero Trust. DockFlare facilite la gestion des IdP et leur intégration dans vos politiques d'accès.

## Vue d'ensemble

Au lieu de vous appuyer uniquement sur une authentification par e-mail, vous pouvez utiliser des fournisseurs OAuth populaires comme Google, GitHub, Azure AD et d'autres encore. Les utilisateurs s'authentifient avec leurs comptes existants, ce qui offre une expérience de connexion fluide et sécurisée.

## Fournisseurs pris en charge

DockFlare prend en charge les fournisseurs d'identité suivants :

- **Google** - Comptes Google grand public
- **Google Workspace** - Comptes Google Workspace (G Suite) avec restriction de domaine facultative
- **Microsoft Azure AD** - Microsoft Entra ID (Azure Active Directory)
- **Okta** - Okta Identity Cloud
- **GitHub** - GitHub OAuth
- **OpenID Connect générique** - Tout fournisseur compatible OIDC

## Gestion des fournisseurs d'identité

### Ajouter un fournisseur d'identité

1. Ouvrez la page **Politiques d'accès**.
2. Dans la section **Fournisseurs d'identité**, cliquez sur **Ajouter un fournisseur**.
3. Renseignez les champs requis :
   - **Nom convivial** : nom interne utilisé par DockFlare, par exemple `google-main` ou `github-dev`
   - **Nom d'affichage** : nom affiché dans le tableau de bord Cloudflare
   - **Type de fournisseur** : sélectionnez votre fournisseur OAuth
   - **Configuration** : informations d'identification propres au fournisseur, selon les guides ci-dessous
4. Cliquez sur **Créer un fournisseur**.
5. Testez le fournisseur avec l'URL de test fournie.

### Synchroniser depuis Cloudflare

Si vous avez déjà configuré des IdP dans Cloudflare Zero Trust :

1. Cliquez sur **Sync depuis Cloudflare** dans la section Fournisseurs d'identité.
2. DockFlare importera tous les IdP existants et générera automatiquement des noms conviviaux.
3. Vous pourrez ensuite renommer ces noms pour les rendre plus faciles à utiliser dans les étiquettes.

### Tester un fournisseur d'identité

Après avoir créé un IdP, vous pouvez le tester :

1. Cliquez sur le menu **⋮** à côté du fournisseur.
2. Sélectionnez **Tester l'IdP**.
3. Une nouvelle fenêtre s'ouvre pour l'authentification.
4. Vérifiez que le flux de connexion fonctionne correctement.

## Guides de configuration des fournisseurs

### Google (comptes personnels)

**Étape 1 : créer les identifiants OAuth**

1. Accédez à [Google Cloud Console](https://console.cloud.google.com/).
2. Créez un nouveau projet ou sélectionnez un projet existant.
3. Ouvrez **API et services** → **Identifiants**.
4. Cliquez sur **Créer des identifiants** → **ID client OAuth**.
5. Sélectionnez **Application Web**.
6. Ajoutez l'URI de redirection autorisé :
   ```
   https://<your-team>.cloudflareaccess.com/cdn-cgi/access/callback
   ```
   <small>Vous trouverez le nom de votre équipe dans <a href="https://one.dash.cloudflare.com/{{ACCOUNT_ID}}/settings/custom_pages" target="_blank">Zero Trust</a>, sous Paramètres > Pages personnalisées.</small>
7. Copiez l'**ID client** et le **secret client**.

**Étape 2 : configurer dans DockFlare**

- **ID client** : collez la valeur depuis Google Cloud Console
- **Secret client** : collez la valeur depuis Google Cloud Console

---

### Google Workspace

Identique à la configuration Google ci-dessus, avec un champ facultatif supplémentaire :

- **Apps Domain** : (facultatif) limitez l'accès à un domaine spécifique, par exemple `example.com`

Si ce champ est renseigné, seuls les utilisateurs possédant une adresse e-mail `@example.com` pourront s'authentifier.

---

### Microsoft Azure AD

**Étape 1 : enregistrer l'application dans Azure**

1. Accédez au [Portail Azure](https://portal.azure.com/).
2. Ouvrez **Azure Active Directory** → **Inscriptions d'applications**.
3. Cliquez sur **Nouvelle inscription**.
4. Donnez un nom à l'application, par exemple `DockFlare Access`.
5. Sous **URI de redirection**, sélectionnez **Web** puis saisissez :
   ```
   https://<your-team>.cloudflareaccess.com/cdn-cgi/access/callback
   ```
   <small>Vous trouverez le nom de votre équipe dans <a href="https://one.dash.cloudflare.com/{{ACCOUNT_ID}}/settings/custom_pages" target="_blank">Zero Trust</a>, sous Paramètres > Pages personnalisées.</small>
6. Cliquez sur **S'inscrire**.
7. Copiez l'**ID d'application (client)**.
8. Copiez l'**ID du répertoire (locataire)**.
9. Ouvrez **Certificats et secrets** → **Nouveau secret client**.
10. Créez un secret et copiez la **Valeur**.

**Étape 2 : configurer dans DockFlare**

- **ID d'application (client)** : collez la valeur depuis Azure
- **ID de répertoire (locataire)** : collez la valeur depuis Azure
- **Secret client** : collez la valeur depuis Azure

---

### GitHub

**Étape 1 : créer l'application OAuth**

1. Accédez aux [Paramètres développeur GitHub](https://github.com/settings/developers).
2. Cliquez sur **Nouvelle application OAuth**.
3. Renseignez les champs :
   - **Nom de l'application** : DockFlare Access
   - **URL de la page d'accueil** : `https://your-domain.com`
   - **URL de rappel d'autorisation** :
     ```
     https://<your-team>.cloudflareaccess.com/cdn-cgi/access/callback
     ```
     <small>Vous trouverez le nom de votre équipe dans <a href="https://one.dash.cloudflare.com/{{ACCOUNT_ID}}/settings/custom_pages" target="_blank">Zero Trust</a>, sous Paramètres > Pages personnalisées.</small>
4. Cliquez sur **Enregistrer l'application**.
5. Copiez l'**ID client**.
6. Cliquez sur **Générer un nouveau secret client** et copiez-le.

**Étape 2 : configurer dans DockFlare**

- **ID client** : collez la valeur depuis GitHub
- **Secret client** : collez la valeur depuis GitHub

---

### Okta

**Étape 1 : créer l'application dans Okta**

1. Connectez-vous à votre [console d'administration Okta](https://admin.okta.com/).
2. Ouvrez **Applications** → **Créer une intégration d'application**.
3. Sélectionnez **OIDC - OpenID Connect**.
4. Choisissez **Application Web**.
5. Configurez :
   - **URI de redirection de connexion** :
     ```
     https://<your-team>.cloudflareaccess.com/cdn-cgi/access/callback
     ```
     <small>Vous trouverez le nom de votre équipe dans <a href="https://one.dash.cloudflare.com/{{ACCOUNT_ID}}/settings/custom_pages" target="_blank">Zero Trust</a>, sous Paramètres > Pages personnalisées.</small>
6. Cliquez sur **Enregistrer**.
7. Copiez l'**ID client** et le **secret client**.
8. Notez votre **domaine Okta**, par exemple `https://dev-12345.okta.com`.

**Étape 2 : configurer dans DockFlare**

- **URL du compte Okta** : votre domaine Okta, par exemple `https://dev-12345.okta.com`
- **ID client** : collez la valeur depuis Okta
- **Secret client** : collez la valeur depuis Okta

---

### OpenID Connect générique

Pour tout fournisseur compatible OIDC :

**Étape 1 : récupérer la configuration du fournisseur**

Dans la documentation de votre IdP, récupérez :
- URL d'autorisation
- URL du jeton
- URL JWKS (JSON Web Key Set)
- ID client
- Secret client

**Étape 2 : configurer dans DockFlare**

- **URL d'autorisation** : endpoint OAuth d'autorisation du fournisseur
- **URL du jeton** : endpoint de jeton du fournisseur
- **URL JWKS** : endpoint JWKS du fournisseur, utilisé pour vérifier la signature
- **ID client** : valeur fournie par votre fournisseur
- **Secret client** : valeur fournie par votre fournisseur

---

## Utiliser les fournisseurs d'identité dans les politiques d'accès

### Dans les groupes d'accès

1. Ouvrez **Politiques d'accès** → **Politiques d'accès avancées**.
2. Cliquez sur **Créer un nouveau groupe** ou modifiez un groupe existant.
3. Dans la section **Règles de stratégie** :
   - **Fournisseurs d'identité** : sélectionnez un ou plusieurs IdP
   - **E-mails ou domaines autorisés** : **obligatoire lorsque vous utilisez des IdP**. Indiquez les adresses e-mail autorisées.
4. Enregistrez le groupe.

### Modes d'authentification

Deux options sont disponibles :

1. **E-mail uniquement** : saisissez des adresses e-mail sans sélectionner d'IdP. Les utilisateurs s'authentifient alors via un code PIN à usage unique.
2. **IdP + e-mail (obligatoire)** : sélectionnez un ou plusieurs IdP et saisissez les e-mails autorisés. Les utilisateurs doivent s'authentifier via l'IdP sélectionné et figurer dans la liste des e-mails autorisés.

**⚠️ Avis de sécurité :** lorsque vous utilisez des fournisseurs d'identité, vous **devez** spécifier les adresses e-mail autorisées. Cela évite les accès non autorisés. Par exemple, sans restriction sur les adresses e-mail, sélectionner `Google` comme IdP permettrait à n'importe quel utilisateur disposant d'un compte Google d'accéder à votre service.

### Dans les étiquettes Docker

Utilisez le nom convivial dans les étiquettes de vos conteneurs :

```yaml
services:
  myapp:
    image: myapp:latest
    labels:
      dockflare.enable: "true"
      dockflare.hostname: "app.example.com"
      dockflare.access.group: "my-access-group"
```

Le groupe d'accès `my-access-group` résout automatiquement les noms conviviaux des IdP en UUID Cloudflare.

---

## Bonnes pratiques

### Conventions de nommage

Utilisez des noms conviviaux, clairs et descriptifs :
- ✅ `google-main`, `github-dev`, `azure-work`
- ❌ `idp1`, `test`, `new`

### Sécurité

- **Faites tourner régulièrement les secrets** : mettez à jour périodiquement les secrets client
- **Limitez le périmètre** : pour Google Workspace et Azure AD, limitez l'accès à des domaines spécifiques quand c'est possible
- **Testez avant la production** : testez toujours les IdP avant de les appliquer à des services de production
- **Surveillez l'utilisation** : consultez les journaux Cloudflare afin de détecter les tentatives d'accès non autorisées

### Environnements multiples

Créez des IdP distincts pour chaque environnement :
- `google-dev` - Environnement de développement
- `google-staging` - Environnement de préproduction
- `google-prod` - Environnement de production

### Exigences e-mail avec les IdP

**IMPORTANT :** l'authentification via IdP nécessite toujours des restrictions sur les adresses e-mail pour des raisons de sécurité.

**Exemple de groupe d'accès :**
- **Fournisseurs d'identité** : `google-main`
- **E-mails autorisés** : `admin@example.com, user@example.com, @contractor-domain.com`

Cette configuration autorise l'accès aux utilisateurs qui :
- S'authentifient via l'IdP `google-main` (Google OAuth) **ET**
- Possèdent une adresse e-mail correspondant à `admin@example.com`, `user@example.com` ou à n'importe quelle adresse `@contractor-domain.com`

**Fonctionnement :**
1. L'utilisateur clique sur le bouton de connexion dans l'application protégée.
2. Il est redirigé vers la page de connexion Google OAuth.
3. Après l'authentification Google, Cloudflare vérifie si son e-mail figure dans la liste autorisée.
4. L'accès n'est accordé que si l'adresse e-mail correspond à la liste des adresses autorisées.

---

## Dépannage

### Erreur « URI de redirection non valide »

**Cause :** l'URI de redirection configuré dans le fournisseur OAuth ne correspond pas à celui attendu par Cloudflare.

**Solution :** assurez-vous d'avoir ajouté exactement cet URI :
```
https://<your-team>.cloudflareaccess.com/cdn-cgi/access/callback
```
<small>Vous trouverez le nom de votre équipe dans <a href="https://one.dash.cloudflare.com/{{ACCOUNT_ID}}/settings/custom_pages" target="_blank">Zero Trust</a>, sous Paramètres > Pages personnalisées.</small>

Remplacez `<your-team>` par le nom de votre équipe Cloudflare Zero Trust.

---

### « Le test de l'IdP a échoué »

**Cause :** identifiants incorrects ou configuration erronée.

**Solution :**
1. Vérifiez que l'ID client et le secret client sont corrects.
2. Vérifiez que l'application OAuth est activée chez votre fournisseur.
3. Pour Azure AD, vérifiez à la fois l'ID client et l'ID tenant.
4. Testez le fournisseur avec l'URL de test de Cloudflare.

---

### « Impossible de supprimer l'IdP géré par le système »

**Cause :** vous essayez de supprimer le fournisseur One-Time PIN intégré.

**Solution :** le fournisseur `onetimepin` est géré par le système et ne peut pas être supprimé. Il est nécessaire à l'authentification OTP basée sur l'e-mail.

---

### « IdP introuvable dans l'étiquette Docker »

**Cause :** l'étiquette utilise l'UUID Cloudflare au lieu du nom convivial.

**Solution :** utilisez le nom convivial, par exemple `google-main`, à la place de l'UUID dans la configuration de votre groupe d'accès.

---

## Documentation associée

- [Bonnes pratiques des politiques d'accès](Access-Policy-Best-Practices.md)
- [Politiques de zone par défaut](Zone-Default-Policies.md)
- [Étiquettes des conteneurs](Container-Labels.md)
- [Architecture de sécurité](Security-Architecture.md)

---
