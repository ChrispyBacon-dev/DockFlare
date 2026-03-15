# Mehri Domains bruuche (indexierti Labels)

Mit **indexierte Labels** chasch für e einzige Container mehri unabhängigi Ingress-Regle definieren. Das isch praktisch, wänn e Dienst mehri Ports oder Pfäd het, wo under verschidene Hostname söue laufe.

## Wie s funktioniert

Für mehri Regle setzisch du vor d normale DockFlare-Labels e Zahl mit Punkt, aafangend bi `0`. Zum Bispil `dockflare.0.hostname`, `dockflare.1.hostname` usw.

* Jede Zahl (`0`, `1`, `2`) isch e eigeti Ingress-Regel.
* E indexierte Hostname-Label isch immer dr Startpunkt für e neui Regel.
* Alli andere Labels mit em glyche Index gälte nume für die Regel.

## Dr Fallback-Mechanismus

Wänn für e indexierti Regel es Feld fählt, nimmt DockFlare dr Wert vom passende **Basis-Label** ohni Index.

So chasch gemeinsame Istellige einisch definiere u nume pro Regel d Abwychige überschrybe.

## Bispil: E Web UI u e API freigäh

Näh mer aa, e Container liefert e Webapp uf Port `80` u e API uf Port `3000`. D Webapp söll under `app.example.com` laufe, d API under `api.example.com`. D API söll mit ere Access Group gsichert sy, d Hauptapp aber öffentlich blybe.

So cha das usgseh:

```yaml
services:
  my-app:
    image: my-application
    restart: unless-stopped
    networks:
      - cloudflare-net
    labels:
      - "dockflare.enable=true"

      # --- Base Labels (Fallback) ---
      # This service is used by rule 0, as it's not specified there.
      - "dockflare.service=http://my-app:80" 

      # --- Rule 0: The Web UI ---
      - "dockflare.0.hostname=app.example.com"
      # No 'service' label here, so it falls back to the base one.
      # No 'access.group' label, so it's public.

      # --- Rule 1: The API ---
      - "dockflare.1.hostname=api.example.com"
      # Override the service to point to the API port.
      - "dockflare.1.service=http://my-app:3000"
      # Add a specific access policy for this rule only.
      - "dockflare.1.access.group=api-users-policy"
```

### Was da passiert

* **Regel 0 (`app.example.com`)**:
  * het `dockflare.0.hostname`
  * het kes eigets `dockflare.0.service`, drum gilt dr Basis-Wärt `http://my-app:80`
  * isch öffentlich, wiu kei Access Group gsetzt isch

* **Regel 1 (`api.example.com`)**:
  * het `dockflare.1.hostname`
  * überschrybt dr Dienst mit `dockflare.1.service=http://my-app:3000`
  * bruucht mit `dockflare.1.access.group` e eigeti Sicherheitsrichtlinie

So blybt dini `docker-compose.yml` sauberer, klarer u besser wartbar.
