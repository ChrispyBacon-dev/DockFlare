# Architecture de sécurité et renforcement de DockFlare

Ce document explique comment DockFlare protège à la fois le nœud Master et les agents inscrits dans DockFlare 3.0+. Il complète l'audit de sécurité en récapitulant les mécanismes de protection intégrés à DockFlare ainsi que les pratiques opérationnelles recommandées.

## 1. Modèle de confiance du plan de contrôle

- **Le Master comme source de vérité** – Le DockFlare Master détient toutes les informations d'identification Cloudflare et toutes les définitions de politiques. Les agents ne gèrent jamais directement les jetons API ; ils exécutent uniquement des instructions reçues via un canal authentifié.
- **Clés API par agent** – L'inscription nécessite une clé API unique émise par le Master. Ces clés sont stockées dans le magasin chiffré `agent_keys.dat` avec leurs métadonnées (propriétaire, horodatages, statut), ce qui permet de les faire tourner ou de les révoquer à tout moment.
- **Protection de l'API du Master** – Les endpoints administratifs, y compris l'interface web et `/api/v2/*`, nécessitent soit une session valide, soit la clé API du Master. Les jetons sont masqués dans les réponses et les logs, et peuvent être renouvelés sans redémarrer la stack.

## 2. Configuration chiffrée et gestion des clés

- **`dockflare_config.dat` chiffré** – Les identifiants Cloudflare, les comptes de l'interface, les valeurs par défaut du tunnel et la clé du Master sont stockés dans un blob chiffré protégé par `dockflare.key`.
- **Registre des agents chiffré** – Les clés API des agents ainsi que leurs métadonnées d'audit sont stockées dans `agent_keys.dat`, chiffré avec la même clé Fernet. Les informations sensibles n'apparaissent plus dans `state.json`.
- **Redémarrage automatique après restauration** – Lorsqu'une archive de sauvegarde est restaurée, DockFlare écrit les artefacts chiffrés, recharge l'état d'exécution, dépose un indicateur de redémarrage, puis s'arrête. La politique de redémarrage de Docker relance immédiatement le conteneur avec la nouvelle configuration.
- **`state.json` en clair pour l'observabilité** – `state.json` reste en texte brut afin que les opérateurs puissent inspecter facilement les règles et les agents. Les fichiers chiffrés restent la source de référence pour les secrets.

## 3. Garanties de sauvegarde et de restauration

- **Contenu de l'archive** – Chaque archive de sauvegarde (`dockflare_backup_*.zip`) contient `dockflare_config.dat`, `dockflare.key`, `agent_keys.dat`, `state.json` ainsi qu'un `manifest.json` avec les checksums et les métadonnées de version. Aucun autre fichier n'est nécessaire pour reconstruire un nœud Master.
- **Flux de restauration automatisé** – Une restauration via l'assistant de configuration ou la page Settings écrit les artefacts, recharge les caches d'exécution et force le redémarrage du conteneur afin que la configuration chiffrée soit appliquée immédiatement.
- **Compatibilité héritée** – Le téléversement d'un `state.json` autonome reste pris en charge pour le dépannage ou les migrations partielles. DockFlare importe l'état d'exécution, mais conserve la configuration chiffrée existante, ce qui évite les réinitialisations accidentelles d'identifiants.

## 4. Sécurité réseau et communication

- **Transport via Cloudflare Tunnel** – Les agents n'exposent aucun port entrant. Tout le trafic passe par le tunnel Cloudflare géré par le Master, ce qui réduit la surface d'attaque sur les hôtes distants.
- **Appels d'agents authentifiés** – Les appels REST des agents incluent leur clé API et sont liés à leur identifiant enregistré. Les tokens non valides ou révoqués sont refusés.
- **Couche Redis partagée** – DockFlare s'appuie sur Redis pour le cache, le streaming des logs et la signalisation inter-threads. La stack Compose recommandée maintient Redis sur un réseau `dockflare-internal` dédié, afin que les workloads présents sur `cloudflare-net` ne puissent pas l'atteindre directement. Si vous utilisez un Redis externe, sécurisez-le avec authentification et TLS.
- **Exécution au moindre privilège** – Le Master comme les agents s'exécutent sous l'utilisateur `dockflare` (UID/GID 65532) et n'accèdent à Docker qu'au travers du socket proxy fourni, ce qui limite fortement la surface d'API exposée.

## 5. Authentification et autorisation

- **Connexion renforcée à l'interface web** – L'assistant de configuration initiale impose la création d'un compte administrateur pour l'interface web. La connexion par mot de passe peut être désactivée, mais **cela est fortement déconseillé** en raison des implications de sécurité sur le réseau Docker.
- **Gestion des sessions** – Les sessions Flask-Login sont liées à la configuration chiffrée. Restaurer une sauvegarde ou faire tourner les identifiants invalide automatiquement les sessions existantes.
- **ACL des agents** – Chaque fiche agent enregistre l'affectation du tunnel, les horodatages de heartbeat et les commandes en attente. Le Master n'envoie des commandes qu'aux agents présentant le bon jeton et un statut d'inscription valide.

### ⚠️ Important : avertissement de sécurité « Disable Password Login »

DockFlare propose un réglage **Disable Password Login**, destiné aux déploiements avancés dans lesquels DockFlare est déjà protégé par une couche d'authentification externe, par exemple Cloudflare Access. **Nous déconseillons fortement d'utiliser cette option** dans la majorité des cas.

**Risques de sécurité lorsqu'elle est activée :**
- **Tous les endpoints API deviennent accessibles sans authentification**
- **Exposition via le réseau Docker** : même si DockFlare est protégé par Cloudflare Access sur Internet, les conteneurs du même réseau Docker peuvent contourner cette authentification externe et accéder directement à l'API de DockFlare
- **Aucun contrôle d'authentification côté application** : l'application suppose que toute la sécurité est gérée en amont

**Exemple de vecteur d'attaque :**
```
Internet → Cloudflare Access (Protected) → DockFlare ✅
         ↓
Docker Network → Other Container → DockFlare API (Unprotected) ❌
```

**Approche recommandée :**
Plutôt que de désactiver l'authentification par mot de passe, utilisez l'une de ces solutions sûres :
1. **Identifiants locaux DockFlare** - Authentification simple par mot de passe intégrée à DockFlare
2. **Fournisseurs OAuth/OIDC** - Configurez Google, GitHub, Azure AD ou d'autres fournisseurs d'identité pour bénéficier du single sign-on sans compromettre la sécurité

Dans les deux cas, vous conservez une authentification correcte tout en profitant du confort du SSO. L'option OAuth apporte cette expérience sans exposer les risques liés à une authentification désactivée.

**En résumé :** sauf si vous disposez d'une architecture de sécurité très spécifique, bien comprise et correctement isolée au niveau réseau, laissez la connexion par mot de passe activée et utilisez OAuth pour plus de confort.

## 6. Audit et visibilité opérationnelle

- **Suivi des métadonnées** – Les clés d'agents enregistrent `created_at`, `last_used_at`, `bound_agent_id`, leur état et les événements de révocation. `state.json` reflète également l'horodatage de dernière activité des agents pour faciliter les contrôles de santé.
- **Streaming des logs** – Les logs temps réel transitent via Redis pub/sub. Les valeurs sensibles, comme les jetons et les clés, sont masquées avant d'être envoyées au client.
- **API d'état** – `/api/v2/overview` consolide l'état des tunnels, des agents et de la configuration pour les systèmes de supervision ou les workflows GitOps.

## 7. Recommandations de déploiement

| Zone | Recommandation |
| --- | --- |
| Volumes Docker | Conservez `/app/data` pour la configuration chiffrée, les clés et l'état. Conservez aussi `/app/logs` si la journalisation sur fichier est activée, et vérifiez que les montages hôte sont accessibles en écriture par l'UID/GID 65532 ou par vos arguments de build personnalisés. |
| Redis | Exécutez `redis:7-alpine` aux côtés de DockFlare sur un réseau privé (`dockflare-internal`) ou pointez `REDIS_URL` vers une instance durcie avec authentification/TLS. Évitez d'exposer Redis publiquement. Utilisez `REDIS_DB_INDEX` pour isoler les données DockFlare d'autres conteneurs partageant la même instance Redis. |
| Sauvegardes | Téléchargez régulièrement le `.zip` et stockez-le avec `dockflare.key`. Les deux fichiers sont nécessaires pour déchiffrer la configuration lors d'une restauration. |
| Agents | Traitez les clés API comme des identifiants sensibles. Déployez les agents avec le socket proxy afin que seuls les endpoints Docker nécessaires soient exposés. Gardez en tête que le conteneur tourne sous l'utilisateur non privilégié `dockflare` (UID/GID 65532) ; ajustez les permissions de l'hôte ou reconstruisez avec un `DOCKFLARE_UID/DOCKFLARE_GID` adapté. |
| Reverse proxy | Placez DockFlare derrière Cloudflare Access ou un autre IdP de confiance. Si vous désactivez la connexion par mot de passe, assurez-vous que l'authentification en amont reste toujours appliquée. |
| Monitoring | Déclenchez des alertes en cas de redémarrages inattendus, de heartbeats manquants ou de nouvelle émission de clé en dehors des fenêtres de maintenance. |

## 8. Améliorations futures (feuille de route)

- Protection optionnelle de la clé Fernet au repos via une passphrase.
- Rotation automatisée des clés d'agents avec périodes de grâce pour des déploiements progressifs.
- Portées de commandes granulaires pour séparer les opérations en lecture seule des opérations de mutation.

---

DockFlare continue d'évoluer avec la sécurité comme priorité. Consultez régulièrement les notes de version pour suivre les améliorations de renforcement et proposez vos idées via l'issue tracker si vous avez besoin de contrôles supplémentaires.
