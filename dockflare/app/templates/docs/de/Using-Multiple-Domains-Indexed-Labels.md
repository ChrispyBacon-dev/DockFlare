# Verwendung mehrerer Domains (Indexierte Labels)

DockFlare bietet eine leistungsstarke Funktion namens **indexierte Labels**, mit der Sie mehrere unabhängige Ingress-Regeln für einen einzigen Container definieren können. Dies ist besonders nützlich, wenn Sie verschiedene Ports oder Pfade desselben Dienstes unter verschiedenen öffentlichen Hostnamen bereitstellen möchten.

## Wie es funktioniert

Um mehrere Regeln zu erstellen, setzen Sie einfach eine Ganzzahl und einen Punkt als Präfix vor die standardmäßigen DockFlare-Labels, beginnend bei `0`. Zum Beispiel `dockflare.0.hostname`, `dockflare.1.hostname` und so weiter.

*   Jeder Index (z.B. `0`, `1`, `2`) repräsentiert eine separate Ingress-Regel.
*   Ein indexierter Hostname (z.B. `dockflare.<index>.hostname`) ist immer erforderlich, um eine neue Regel zu initiieren.
*   Andere Labels im gleichen Index (z.B. `dockflare.<index>.service`) gelten nur für diese spezifische Regel.

## Der Fallback-Mechanismus

Ein Hauptmerkmal von indexierten Labels ist der Fallback-Mechanismus. Wenn Sie kein spezifisches indexiertes Label für eine Regel bereitstellen, greift diese auf den Wert des entsprechenden (nicht indexierten) **Basis-Labels zurück**.

Dies ermöglicht es Ihnen, gemeinsame Einstellungen einmal auf Basis-Ebene zu definieren und nur die spezifischen Werte zu überschreiben, die sich für jede indexierte Regel ändern müssen.

## Beispiel: Freigabe einer Web-UI und einer API

Nehmen wir an, Sie haben einen einzelnen Container, der sowohl eine Webanwendung auf Port `80` als auch eine separate API auf Port `3000` bereitstellt. Sie möchten diese unter `app.example.com` bzw. `api.example.com` zugänglich machen. Außerdem möchten Sie die API mit einer spezifischen Access Group sichern, während die Hauptanwendung öffentlich bleibt.

So würden Sie dies mit indexierten Labels konfigurieren:

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
    *   Definiert kein `dockflare.0.service`, greift also auf das Basis-Label `dockflare.service` zurück und verwendet `http://my-app:80`.
    *   Es ist ein öffentlicher Dienst, da weder für diesen Index noch auf Basis-Ebene eine Zugriffsrichtlinie definiert ist.

*   **Regel 1 (`api.example.com`)**:
    *   Definiert `dockflare.1.hostname`.
    *   Es **überschreibt** den Dienst mit `dockflare.1.service`, der auf den API-Port `3000` verweist.
    *   Wendet eine spezifische Sicherheitsrichtlinie mithilfe von `dockflare.1.access.group` an. Dieses Label betrifft nur diese Regel.

Dieser Ansatz hält Ihre Label-Konfiguration sauber, vermeidet Wiederholungen und macht Ihre `docker-compose.yml`-Dateien leichter lesbar und wartbar.
