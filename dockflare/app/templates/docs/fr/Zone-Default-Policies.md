# Politiques par défaut de zone – Protection contre les caractères génériques

## Aperçu

Les politiques par défaut de zone sont une fonctionnalité de bonne pratique en matière de sécurité qui utilise les applications génériques Cloudflare Access (`*.domain.com`) pour protéger automatiquement tous les sous-domaines d'une zone DNS.

## Le problème que cela résout

Sans stratégies par défaut de zone :
- Les services oubliés sont exposés publiquement
- Les nouveaux sous-domaines n'ont aucune protection jusqu'à ce qu'ils soient configurés manuellement
- Les fautes de frappe dans les configurations de nom d'hôte contournent les contrôles d'accès
- La dérive de la documentation entraîne des failles de sécurité

## Comment ça marche

### Priorité politique

Cloudflare évalue les politiques d'accès dans cet ordre :

1. **Correspondance exacte du nom d'hôte** (par exemple, `app.example.com`)
2. **Correspondance générique** (par exemple, `*.example.com`)
3. **Aucune correspondance** = Accès public (pas d'application Access)

### Implémentation de DockFlare

Section **Politiques de zone par défaut** de DockFlare :
- Répertorie toutes vos zones DNS Cloudflare
- Affiche l'état de protection avec des badges visuels
- Permet la création en un clic de politiques `*.zone.com`
- Vous permet de choisir quel groupe d'accès protège la zone

## Guide de configuration

### Étape 1 : Vérifiez vos zones

1. Accédez à la page **Politiques d'accès**.
2. Faites défiler jusqu'à **Politiques de zone par défaut (*.tld Wildcards)**
3. Vérifiez l'état de protection :
   - 🛡️ **Vert "Protégé"** - La zone a une politique de caractères génériques
   - ⚠️ **Jaune "Non protégé"** - La zone est vulnérable

### Étape 2 : Créer des stratégies de zone

Pour chaque zone non protégée :

1. Cliquez sur le bouton **Créer une stratégie**
2. La fenêtre modale affiche le nom d'hôte `*.zone-name.com`
3. Sélectionnez la politique d'accès appropriée :
   - **Zones publiques** → `public-default-bypass`
   - **Zones internes** → Politique d'authentification
   - **Zones mixtes** → Politique la plus restrictive
4. Cliquez sur **Créer une stratégie de zone**

### Étape 3 : Vérifiez dans Cloudflare

1. Ouvrez le tableau de bord Cloudflare Zero Trust
2. Accédez à Accès → Applications
3. Recherchez les applications nommées `Zone Default: *.domain.com`
4. Vérifiez que la politique est correcte

## Recommandations de sécurité

### Environnements de production

✅ **Toujours activer les politiques par défaut de zone**
- Empêche l'exposition accidentelle
- Détecte les erreurs de configuration
- Protège contre les attaques de découverte de sous-domaines

### Stratégie de sélection des politiques

- **Domaines de contenu public** (blogs, marketing) : `public-default-bypass`
- **Domaines d'outils internes** : authentification par e-mail/domaine
- **Domaines de données sensibles** : authentification compatible MFA
- **Domaines de développement** : verrouillage avec la politique la plus stricte

### Surveillance

Révisez régulièrement :
- Quelles zones sont protégées (page **Politiques d'accès**)
- Accéder aux journaux d'application dans Cloudflare
- Liste des sous-domaines actifs par rapport aux politiques configurées

## Dépannage

### Erreur "La stratégie existe déjà"

Une application d’accès `*.domain.com` existe déjà. Cela pourrait être :
- Créé manuellement dans Cloudflare
- Créé précédemment par DockFlare
- Créé par un autre outil

**Solution :** Gérez-le directement dans Cloudflare, ou supprimez et recréez via DockFlare.

### Service toujours accessible sans authentification

Vérifiez la priorité de la stratégie :
1. Vérifiez que le service a une politique de nom d'hôte spécifique
2. Confirmez que le caractère générique de zone existe et est correctement configuré
3. Si le service doit être public malgré la protection de la zone, ajoutez l'étiquette `dockflare.access.group=public-default-bypass`

### Contournement de la protection de zone pour les services publics

Si vous disposez d'une politique d'authentification au niveau de la zone mais que vous avez besoin de services spécifiques pour rester publics :

1. Ajoutez l'étiquette de contournement au conteneur :
   ```yaml
   labels:
     - "dockflare.access.group=public-default-bypass"
   ```
2. Cela crée une application d'accès au nom d'hôte exact avec décision de contournement
3. Les politiques de nom d'hôte exactes remplacent les politiques de caractères génériques
4. Le service devient accessible au public tandis que la zone reste protégée

Ensuite :
- Vérifiez les journaux d'accès Cloudflare pour confirmer l'ordre d'évaluation des politiques.
- Assurez-vous que l'enregistrement DNS pointe vers le tunnel correct.

### Zone non affichée dans la liste

Causes possibles :
- Zone DNS pas dans votre compte Cloudflare
- Le jeton API ne dispose pas de l'autorisation `Zone:Zone:Read`
- La zone est en pause ou supprimée

**Solution :** Vérifiez que la zone existe dans le tableau de bord Cloudflare et que le jeton API dispose des autorisations correctes.

## Meilleures pratiques

1. **Créez d'abord des politiques de zone** - Avant d'ajouter des services
2. **Utilisez l'authentification pour les zones internes** - N'utilisez jamais de contournement
3. **Documenter les exceptions** - Si une zone n'a pas besoin de protection, documentez pourquoi
4. **Audits réguliers** - Examen mensuel de l'état de protection des zones
5. **Test avant la production** – Vérifiez que la politique relative aux caractères génériques n'interrompt pas les services existants
6. **Principe du moindre privilège** – Utiliser la politique la plus restrictive qui autorise toujours un accès légitime

## Exemples de configurations

### Zone de blogs publics
```
Zone: blog.example.com
Policy: public-default-bypass
Result: All subdomains publicly accessible (*.blog.example.com)
```

### Zone d'outils internes
```
Zone: internal.company.com
Policy: Company Email Authentication
Result: All subdomains require @company.com email (*.internal.company.com)
```

### Zone de Développement Mixte
```
Zone: dev.company.com
Policy: Developer Team Authentication
Result: All dev services protected by default (*.dev.company.com)
Specific overrides: public-demo.dev.company.com → public-default-bypass
```

## Comprendre la priorité des politiques

### Scénario 1 : Une stratégie spécifique remplace le caractère générique

**Configuration :**
- Politique de zone : `*.example.com` → Nécessite une authentification
- Politique spécifique : `blog.example.com` → `public-default-bypass`

**Résultat :**
- `blog.example.com` → Public (une politique spécifique gagne)
- `api.example.com` → Nécessite une authentification (un caractère générique l'attrape)
- `forgotten.example.com` → Nécessite une authentification (un caractère générique l'attrape)

### Scénario 2 : Wildcard comme filet de sécurité

**Configuration :**
- Politique de zone : `*.internal.company.com` → Nécessite une adresse e-mail @company.com
- Politique spécifique : Aucune pour `test-server.internal.company.com`

**Résultat :**
- `test-server.internal.company.com` → Nécessite une authentification (un caractère générique le protège)
- Même si vous avez oublié de le configurer, la politique de zone le protège

### Scénario 3 : Aucune protection

**Configuration :**
- Politique de zone : Aucune pour `*.risky-domain.com`
- Politique spécifique : `app.risky-domain.com` → Authentification

**Résultat :**
- `app.risky-domain.com` → Nécessite une authentification (politique spécifique)
- `forgotten.risky-domain.com` → ⚠️ **PUBLIC** (pas de caractère générique pour l'attraper)

## Intégration avec les étiquettes DockFlare

### Utilisation de l'étiquette `default_tld`

L'étiquette `dockflare.access.policy=default_tld` indique à DockFlare d'utiliser la stratégie de caractère générique de la zone :

```yaml
services:
  my-service:
    image: nginx
    labels:
      - "dockflare.enable=true"
      - "dockflare.hostname=new-app.internal.company.com"
      - "dockflare.service=http://my-service:80"
      - "dockflare.access.policy=default_tld"
```

**Comportement :**
- Si `*.internal.company.com` existe → Hérite de cette politique
- Si aucune politique de zone n'existe → Le service est public (aucune application d'accès créée)

### Recommandation

Au lieu de vous fier à l'étiquette `default_tld` :
1. Créez des politiques de zone par défaut dans l'interface utilisateur
2. Laissez la politique de caractères génériques protéger automatiquement tous les services
3. Créez uniquement des politiques spécifiques pour les exceptions

Cela garantit une meilleure sécurité par défaut.

## Documentation connexe

- [Bonnes pratiques en matière de politique d'accès](Access-Policy-Best-Practices.md)
- [Utilisation de l'interface web](Using-the-Web-UI.md)
- [Étiquettes des conteneurs](Container-Labels.md)
- [Comment fonctionne DockFlare](How-DockFlare-Works.md)
- [Architecture de sécurité](Security-Architecture.md)
