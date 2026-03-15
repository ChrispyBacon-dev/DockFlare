# Accéder à l'interface utilisateur Web

Une fois que vous avez démarré avec succès le conteneur DockFlare, vous pouvez accéder à l'interface utilisateur Web pour gérer vos paramètres, afficher l'état de vos tunnels et configurer manuellement les règles d'entrée.

## URL par défaut

Par défaut, l'interface utilisateur Web de DockFlare est accessible sur le port `5000`. Pour y accéder, ouvrez votre navigateur Web et accédez à l'URL suivante :

```
http://<your-server-ip>:5000
```

Remplacez `<your-server-ip>` par l'adresse IP du serveur sur lequel DockFlare est exécuté.

## Première configuration

La première fois que vous accédez à l'interface utilisateur Web, vous serez guidé par l'**assistant de configuration initiale**. Cet assistant vous aide à :

1. Restaurer une archive de sauvegarde DockFlare existante (`dockflare_backup_*.zip`). Si vous choisissez cette option, le système importe vos clés chiffrées de configuration, d'état et d'agent, puis redémarre automatiquement le conteneur pour les appliquer.
2. Créer un compte administrateur et un mot de passe pour l'interface utilisateur Web.
3. Fournir votre identifiant de compte Cloudflare, votre identifiant de zone (facultatif) et votre jeton API.
4. Confirmer les paramètres du tunnel et terminer les étapes d'intégration.

## Connexion

Après la configuration initiale, un écran de connexion vous sera présenté à chaque fois que vous accédez à l'interface utilisateur Web. Utilisez le mot de passe que vous avez créé lors du processus de configuration pour vous connecter.

## Désactivation de la connexion par mot de passe

DockFlare inclut un paramètre « Désactiver la connexion par mot de passe » destiné aux déploiements avancés où DockFlare lui-même est protégé par une couche d'authentification externe (comme Cloudflare Access). **Nous déconseillons fortement d'utiliser cette fonctionnalité** pour la plupart des déploiements.

### Pourquoi ce paramètre existe

Si vous exécutez DockFlare derrière Cloudflare Access ou un autre proxy d'authentification qui applique le SSO avant d'atteindre l'application, vous pouvez désactiver la connexion par mot de passe intégrée de DockFlare pour éviter la double authentification.

### Risques de sécurité lorsqu'il est activé

- ⚠️ **Tous les points de terminaison de l'API deviennent accessibles sans authentification** lorsque ce paramètre est activé
- ⚠️ **Exposition du réseau Docker :** Même si DockFlare est derrière Cloudflare Access sur l'Internet public, les conteneurs sur le même réseau Docker peuvent contourner l'authentification externe et accéder directement à l'API de DockFlare
- ⚠️ **Aucune application d'authentification :** L'application suppose que l'authentification externe gère la sécurité

### Exemple de vecteur d'attaque

```
Internet → Cloudflare Access (Protected) → DockFlare ✅
         ↓
Docker Network → Other Container → DockFlare API (Unprotected) ❌
```

Même lorsque DockFlare est protégé par Cloudflare Access depuis Internet, tout conteneur exécuté sur le même réseau Docker peut contourner cette protection et accéder directement aux points de terminaison de l'API de DockFlare sans authentification.

### Approche recommandée

Au lieu de désactiver l'authentification par mot de passe, utilisez l'une de ces options sécurisées :

1. **Identifiants DockFlare locaux** - Authentification par mot de passe simple intégrée à DockFlare
2. **Fournisseurs OAuth/OIDC** : configurez Google, GitHub, Azure AD ou d'autres fournisseurs d'identité pour une authentification unique facile sans sacrifier la sécurité (voir [Configuration du fournisseur OAuth](OAuth-Provider-Setup.md)).

Les deux options fournissent une authentification appropriée tout en conservant la commodité du SSO. L'option OAuth vous offre une expérience d'authentification unique sans les risques de sécurité liés à l'authentification désactivée.

### Conclusion

À moins que vous ne disposiez d'une architecture de sécurité très spécifique et bien comprise avec isolation du réseau, laissez la connexion par mot de passe activée et utilisez OAuth pour plus de commodité.