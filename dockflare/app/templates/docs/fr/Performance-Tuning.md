# Réglage des performances

Pour la grande majorité des utilisateurs, les paramètres par défaut de DockFlare offrent un bon équilibre entre performances et utilisation des ressources. Toutefois, dans des environnements très vastes ou très dynamiques, vous pouvez bénéficier du réglage de certains paramètres avancés liés aux performances.

Ces paramètres sont configurés via des variables d'environnement dans votre fichier `docker-compose.yml`.

---

## `CLEANUP_INTERVAL_SECONDS`

Cette variable contrôle la fréquence à laquelle la tâche en arrière-plan de DockFlare s'exécute pour nettoyer les ressources expirées (c'est-à-dire les règles des conteneurs arrêtés dont le délai de grâce est écoulé).

* **Par défaut :** `60` secondes
* **Description :** Un intervalle plus court signifie que les ressources obsolètes sont supprimées plus rapidement de votre configuration Cloudflare. Un intervalle plus long réduit la fréquence des vérifications d’antécédents, ce qui peut légèrement réduire l’utilisation des ressources.
* **Quand effectuer le réglage :** Si vous disposez d'un environnement très dynamique avec de nombreux conteneurs de courte durée et que vous souhaitez que leurs ressources soient nettoyées presque immédiatement, vous pouvez réduire cette valeur (par exemple, à `30`). Pour la plupart des utilisateurs, la valeur par défaut convient.

**Exemple :**
```yaml
environment:
  - CLEANUP_INTERVAL_SECONDS=30
```

---

## `MAX_CONCURRENT_DNS_OPS`

Cette variable définit le nombre maximum d'opérations DNS simultanées (créer, supprimer) que DockFlare effectuera en même temps.

* **Par défaut :** `3`
* **Description :** Il s'agit d'un bouton de réglage direct des performances pour les environnements comportant un grand nombre de services. Lorsque DockFlare démarre ou lorsque plusieurs conteneurs sont démarrés en même temps, ce paramètre limite le nombre de requêtes parallèles adressées à l'API Cloudflare pour les modifications DNS.
* **Quand régler :** Si vous gérez des centaines de services et remarquez que le démarrage initial ou un déploiement de masse est lent à créer tous les enregistrements DNS, vous pouvez essayer d'augmenter cette valeur (par exemple, à `5` ou `10`). Sachez qu'un réglage trop élevé pourrait entraîner une limitation du débit de l'API Cloudflare.

**Exemple :**
```yaml
environment:
  - MAX_CONCURRENT_DNS_OPS=5
```

---

## `RECONCILIATION_BATCH_SIZE`

Cela contrôle la taille du lot pour diverses tâches de réconciliation en arrière-plan.

* **Par défaut :** `3`
* **Description :** Certaines tâches en arrière-plan dans DockFlare traitent les éléments par lots pour éviter de surcharger le système ou l'API Cloudflare. Ce paramètre contrôle la taille de ces lots.
* **Quand régler :** Il s'agit d'un paramètre très avancé. Pour la plupart des utilisateurs, la valeur par défaut ne doit pas être modifiée. Si vous disposez d’un très grand nombre de règles (plusieurs centaines ou milliers), vous pouvez expérimenter avec une taille de lot légèrement plus grande, mais ce n’est généralement pas nécessaire.

**Exemple :**
```yaml
environment:
  - RECONCILIATION_BATCH_SIZE=5
```

---

## `SCAN_ALL_NETWORKS`

Cette variable modifie la façon dont DockFlare découvre l'adresse IP des conteneurs.

* **Par défaut :** `false`
* **Description :** Par défaut, DockFlare s'attend à ce que le conteneur cible se trouve sur le même réseau Docker que DockFlare lui-même. Lorsque `SCAN_ALL_NETWORKS` est défini sur `true`, DockFlare inspectera tous les réseaux auxquels un conteneur est attaché afin de trouver un réseau partagé.
* **Quand régler :** Cela ne doit être activé que si vous disposez d'une configuration réseau Docker complexe dans laquelle vos conteneurs d'applications ne sont pas sur le même réseau que DockFlare. Sachez que l'activation de cette fonctionnalité peut avoir un impact sur les performances dans les environnements comportant un très grand nombre de réseaux Docker, car cela nécessite davantage de travail d'inspection de la part de DockFlare.

**Exemple :**
```yaml
environment:
  - SCAN_ALL_NETWORKS=true
```
