# Basculer entre les modes

Vous pouvez basculer DockFlare entre les modes **Interne** (par défaut) et **Externe** `cloudflared` à tout moment. Ce guide explique le processus pour une transition en douceur.

Pour une comparaison détaillée des deux modes, veuillez consulter la page [Interne vs. Externe `cloudflared`](Internal-vs-External-cloudflared.md).

---

## Passage du mode interne au mode externe

Ce processus implique de configurer votre propre agent `cloudflared`, puis de demander à DockFlare de l'utiliser.

**Étape 1 : Configurez votre agent `cloudflared` externe**

Tout d’abord, vous devez configurer et exécuter votre propre agent `cloudflared`. Il peut s'agir d'un processus sur le système d'exploitation hôte ou d'un autre conteneur Docker.

* Assurez-vous qu'il est configuré pour utiliser un tunnel Cloudflare spécifique.
* Notez le **Tunnel ID** (UUID).
* Démarrez l'agent et confirmez qu'il fonctionne correctement et qu'il apparaît comme « connecté » dans votre tableau de bord Cloudflare.

**Étape 2 : Reconfigurer et redémarrer DockFlare**

Ensuite, vous devez mettre à jour les variables d'environnement de votre conteneur DockFlare pour lui dire de passer en mode externe.

Dans votre `docker-compose.yml` :
```yaml
services:
  dockflare:
    image: alplat/dockflare:stable
    # ... other settings
    environment:
      # Enable external mode
      - USE_EXTERNAL_CLOUDFLARED=true
      # Provide the ID of your running tunnel
      - EXTERNAL_TUNNEL_ID=your-tunnel-uuid-goes-here
```

**Étape 3 : Déployer le changement**

Exécutez `docker compose up -d` pour recréer le conteneur DockFlare avec les nouvelles variables d'environnement.

Lorsque le conteneur DockFlare mis à jour démarre :
1. Il détectera que `USE_EXTERNAL_CLOUDFLARED` est `true`.
2. Il **arrêtera et supprimera** son propre conteneur `cloudflared-agent` géré.
3. Il commencera à envoyer toutes ses configurations de règles d'entrée au tunnel spécifié par `EXTERNAL_TUNNEL_ID`.

Vos services seront désormais servis par votre agent `cloudflared` géré en externe.

---

## Passage du mode externe au mode interne

Ce processus est plus simple car il implique de laisser DockFlare reprendre le contrôle.

**Étape 1 : reconfigurer DockFlare**

Supprimez les variables d'environnement en mode externe de votre fichier DockFlare `docker-compose.yml`.

```yaml
services:
  dockflare:
    image: alplat/dockflare:stable
    # ... other settings
    environment:
      # Remove the following two lines
      # - USE_EXTERNAL_CLOUDFLARED=true
      # - EXTERNAL_TUNNEL_ID=your-tunnel-uuid-goes-here
```

**Étape 2 : Déployer le changement**

Exécutez `docker compose up -d` pour recréer le conteneur DockFlare.

Lorsque le conteneur DockFlare mis à jour démarre :
1. Il détectera que `USE_EXTERNAL_CLOUDFLARED` est `false`.
2. Il **créera, configurera et démarrera** automatiquement son propre conteneur interne `cloudflared-agent`.
3. Il configurera ce nouvel agent pour utiliser le nom de tunnel défini dans vos paramètres DockFlare.

**Étape 3 : Désactivez votre agent externe**

Une fois que vous avez confirmé que le nouvel agent interne fonctionne correctement et gère le trafic, vous pouvez arrêter et supprimer en toute sécurité votre propre agent `cloudflared`.