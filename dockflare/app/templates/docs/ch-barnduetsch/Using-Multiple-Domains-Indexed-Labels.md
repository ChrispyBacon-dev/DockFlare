# Verwendung mehrerer Domains (Indexierte Labels)

DockFlare bietet eine leistungsstarke Funktion namens **indexierte Labels**, mit der du mehrere unabhängige Ingress-Regeln für einen einzigen Container definieren chöi. Das isch besonders nützlich, wenn du verschiedene Ports oder Pfade desselben Dienstes unter verschiedenen öffentlichen Hostnamen bereitstelle wotsch.

## Wie es funktioniert

Um mehrere Regeln zu erstellen, setz einfach eine Ganzzahl u einen Punkt als Präfix vor die standardmässigen DockFlare-Labels, beginnend bei `0`. zum Biispil `dockflare.0.hostname`, `dockflare.1.hostname` u so weiter.

*   Jeder Index (z.B. `0`, `1`, `2`) repräsentiert eine separate Ingress-Regel.
*   Ein indexierter Hostname (z.B. `dockflare.<index>.hostname`) isch immer nötig, um eine neue Regel zu initiieren.
*   Andere Labels im gleichen Index (z.B. `dockflare.<index>.service`) gelten nur für diese spezifische Regel.

## Der Fallback-Mechanismus

Ein Hauptmerkmal von indexierten Labels isch der Fallback-Mechanismus. Wänn du kei spezifisches indexiertes Label für eine Regel bereitstelle, greift diese auf den Wert des entsprechenden (nid indexierten) **Basis-Labels zurück**.

Das ermöglicht es dir, gemeinsame Istellige einmal auf Basis-Ebene zu definieren u nur die spezifischen Werte zu überschreiben, die sich für jede indexierte Regel ändern müesse.

## Beispiel: Freigabe einer Web UI u einer API

Näh mer aa, du hesch einen einzelnen Container, der sowohl eine Webanwendung auf Port `80` als auch eine separate API auf Port `3000` bereitstellt. Du wotsch diese unter `app.example.com` bzw. `api.example.com` zugänglich machen. Ausserdem wotsch du die API mit einer spezifischen Access Group sichern, während die Hauptanwendung öffentlich bleibt.

So chönnt das mit indexierte Labels usgseh:

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

### Analyse des Beispiels

*   **Regel 0 (`app.example.com`)**:
    *   Definiert `dockflare.0.hostname`.
    *   Definiert kei `dockflare.0.service`, greift also auf das Basis-Label `dockflare.service` zurück u verwendet `http://my-app:80`.
    *   Es isch ein öffentlicher Dienst, da weder für diesen Index noch auf Basis-Ebene eine Zugriffsrichtlinie definiert isch.

*   **Regel 1 (`api.example.com`)**:
    *   Definiert `dockflare.1.hostname`.
    *   Es **überschreibt** den Dienst mit `dockflare.1.service`, der auf den API-Port `3000` verweist.
    *   Wendet eine spezifische Sicherheitsrichtlinie mithilfe von `dockflare.1.access.group` an. Das Label betrifft nur diese Regel.

Dieser Ansatz hält dini Label-Konfiguration sauber, vermeidet Wiederholungen u macht dini `docker-compose.yml`-Dateien leichter lesbar u wartbar.
