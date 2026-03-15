# DockFlare-Agent und Multi-Server-Architektur

DockFlare 3.0 führt ein verteiltes Ausführungsmodell ein, mit dem Sie Cloudflare-Tunnel über mehrere Docker-Hosts hinweg verwalten können. Der DockFlare **Master** koordiniert die Konfiguration, während leichtgewichtige **Agenten** neben Ihren Workloads laufen und ihre lokale `cloudflared`-Instanz mit dem Master synchron halten.

Dieser Leitfaden erklärt die Architektur, das Sicherheitsmodell und den schrittweisen Workflow für die Bereitstellung von Agenten.

---

## Warum Agenten?

* **Compute von der Ingress-Steuerung entkoppeln** – halten Sie Ihre Workloads in der Nähe der Benutzer, während Sie eine einzige Kontrollebene beibehalten.
* **Sichtbarkeit pro Host** – überwachen Sie Heartbeat, Tunnelstatus und Befehlshistorie für jeden Agenten.
* **Token mit geringsten Rechten** – kompromittierte Agenten können widerrufen werden, ohne den Master oder andere Hosts anzutasten.
* **Erhöhte Ausfallsicherheit** – Agenten bedienen den Verkehr weiterhin mit ihrer zuletzt bekannten Konfiguration, wenn der Master vorübergehend nicht erreichbar sein sollte.

---

## Komponenten im Überblick

| Komponente | Verantwortlichkeit |
|-----------|----------------|
| **Master (DockFlare)** | Hostet die Web-UI, speichert den Status, gleicht gewünschte Ingress-Regeln ab und erteilt Befehle. |
| **Redis** | Backplane für Caching, Agenten-Heartbeats und anstehende Befehle in der Warteschlange. |
| **DockFlare Agent** | Headless-Container, der lokale Docker-Ereignisse beobachtet, Befehle ausführt und `cloudflared` betreibt. |
| **cloudflared** | Behandelt die eigentliche Tunnelverbindung zu Cloudflare pro Agent. |

Master und Redis laufen typischerweise zusammen, während Agenten neben Workloads laufen (möglicherweise in anderen Netzwerken).

---

## Voraussetzungen

* DockFlare Master ≥ v3.0 mit konfiguriertem Redis (`REDIS_URL` gesetzt). Optional können Sie `REDIS_DB_INDEX` festlegen, um Daten von anderen Containern zu isolieren, die dieselbe Redis-Instanz verwenden.
* Cloudflare API-Token mit Tunnel- + Access-Berechtigungen (gleich wie in früheren Versionen).
* Docker-Laufzeit auf jedem Host, den Sie verwalten möchten.
* (Optional) Spezielles Netzwerksegment oder VPN zwischen Master und Agenten, wenn Sie den Master nicht öffentlich zugänglich machen.

---

## Workflow-Übersicht

1. **Agenten-API-Schlüssel generieren** in der DockFlare UI (`Agents → Generate Key`).
2. **DockFlare Agent-Container ausrollen** auf dem Remote-Host, wobei Master-URL und Schlüssel übergeben werden.
3. Der Agent **registriert** sich beim Master und erscheint mit dem Status *Ausstehend (Pending)*.
4. In der Master-UI **enrolen Sie den Agenten** (freischalten) – weisen Sie ihm einen Cloudflare Tunnel zu oder erstellen Sie einen neuen Tunnel für diesen Host.
5. Der Master reiht Befehle ein; der Agent **ruft diese ab (polls)**, wendet die Konfiguration an und meldet Status/Heartbeat. DockFlare erkennt die Zielzone für jeden Hostnamen automatisch (und fällt nur auf die Standardzone zurück, wenn die Erkennung fehlschlägt).
6. Wenn Container auf dem Host des Agenten gestartet oder gestoppt werden, streamt der Agent Ereignisse an den Master zurück, der wiederum DNS, Zugriffsrichtlinien und Tunnel-Eingangsregeln aktualisiert.

---

## Bereitstellung des DockFlare Agenten

> ℹ️ Der Agent wird als `alplat/dockflare-agent` veröffentlicht. Solange das öffentliche Repository noch nicht online ist, können Sie ihn aus dem `DockFlare-agent` Source-Tree erstellen, der in DockFlare 3.0 enthalten ist.

```bash
# Example environment file used by the agent container
DOCKFLARE_MASTER_URL=https://dockflare.example.com
DOCKFLARE_API_KEY=agent_api_key_goes_here
DOCKER_HOST=tcp://docker-socket-proxy:2375
# control the docker image used for the managed cloudflared tunnel (accepts repo:tag or repo@sha256:<digest>)
CLOUDFLARED_IMAGE=cloudflare/cloudflared:2025.9.0
LOG_LEVEL=info
TZ=Europe/Zurich
```

Minimale `docker-compose.yml` auf dem Agenten-Host:

```yaml
version: '3.8'

services:
  docker-socket-proxy:
    image: tecnativa/docker-socket-proxy:v0.4.1
    container_name: docker-socket-proxy
    restart: unless-stopped
    environment:
      - DOCKER_HOST=unix:///var/run/docker.sock
      - CONTAINERS=1
      - EVENTS=1
      - NETWORKS=1
      - IMAGES=1
      - POST=1
      - PING=1
      - EXEC=1
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock
    networks:
      - dockflare-internal
      
  dockflare-agent:
    image: alplat/dockflare-agent:latest
    container_name: dockflare-agent
    restart: unless-stopped
    env_file:
      - .env
    environment:
      - DOCKER_HOST=${DOCKER_HOST:-tcp://docker-socket-proxy:2375}
      - TZ=${TZ:-UTC}
      - LOG_LEVEL=${LOG_LEVEL:-info}
    volumes:
      - agent_data:/app/data
    depends_on:
      - docker-socket-proxy
    networks:
      - cloudflare-net
      - dockflare-internal

volumes:
  agent_data:

networks:
  cloudflare-net:
    name: cloudflare-net
    external: true
  dockflare-internal:
    name: dockflare-internal
```

- Führen Sie `docker network create cloudflare-net` einmal aus, um das gemeinsame Netzwerk für Master und Agenten bereitzustellen.
- Der Socket-Proxy begrenzt die Docker-API-Oberfläche, die der Agent erreichen kann; nur die auf `1` gesetzten Fähigkeiten sind erreichbar.
- Das Agenten-Image läuft als der unprivilegierte `dockflare`-Benutzer (UID/GID 65532). Stellen Sie sicher, dass gemountete Verzeichnisse wie `/app/data` von diesem Konto beschrieben werden können, oder erstellen Sie das Image so, dass es Ihren Host-Informationen entspricht.
- Füllen Sie eine `.env`-Datei mit `DOCKFLARE_MASTER_URL` und `DOCKFLARE_API_KEY` aus; optionale Overrides (zum Beispiel `LOG_LEVEL` oder `DOCKER_HOST`) können Sie auf die gleiche Weise setzen.

---

## Sicherheitsmodell

* **Master API Key** – schützt die administrative API. Die UI zeigt ihn erst an, nachdem Sie auf *Show master API key* geklickt haben.
* **Agent API Keys** – eindeutig pro Agent. Ein Widerruf sperrt sofort weitere Registrierungen und Befehle von diesem Host.
* **Redis** – wird für Queues und Caches verwendet; sichern Sie Redis (Passwort + Network ACLs), wenn es außerhalb eines vertrauenswürdigen LANs läuft.
* **Transport** – betreiben Sie den Master hinter HTTPS (zum Beispiel via Cloudflare Access), damit der Agent-Traffic verschlüsselt ist.
* **Least-Privilege Runtime** – der Agent-Container läuft als `dockflare`-User (UID/GID 65532) und verwendet den Socket-Proxy, um Docker-Zugriff auf Container-Inspection und Lifecycle-Operationen zu begrenzen.

### Empfohlene Härtung

1. Bewahren Sie Agent Keys in einem Vault/Passwortmanager auf und rotieren Sie sie regelmäßig.
2. **Deaktivieren Sie das Passwort-Login nicht**: Verwenden Sie stattdessen OAuth/OIDC-Anbieter für SSO, ohne Sicherheitsrisiken zu erzeugen. Falls Sie Passwort-Login unbedingt deaktivieren müssen, beachten Sie, dass Container im selben Docker-Netzwerk externe Authentifizierung umgehen und direkt auf die DockFlare-API zugreifen können. Details siehe [Zugriff auf die Web-UI - Passwort-Anmeldung deaktivieren](Accessing-the-Web-UI.md#passwort-anmeldung-deaktivieren).
3. Nutzen Sie nach Möglichkeit einen eigenen Tunnel pro Agent, um Privilegien sauber zu isolieren.
4. Überwachen Sie in der UI unter `Agents` Heartbeat-Lücken; offline Nodes können direkt aus der UI entfernt werden.

---

## Fehlerbehebung

| Symptom | Lösung |
|---------|--------|
| Agent bleibt in `pending` | Stellen Sie sicher, dass er mit dem richtigen API Key registriert ist, und enrolen Sie ihn in der UI. |
| Commands werden nie abgearbeitet | Prüfen Sie die Redis-Konnektivität und dass die Container-Uhren (Clock) synchron sind. |
| DNS wird nicht aktualisiert | Der Master muss Cloudflare erreichen können und der Agent muss Container-Events senden; prüfen Sie `docker logs dockflare-agent`. |
| Heartbeat ist offline | Prüfen Sie den Network Path zwischen Agent und Master; häufige Ursachen sind Firewall- oder TLS-Probleme. |

---

## Nächste Schritte

* Überprüfen Sie den aktualisierten Schnellstart im README, um sicherzustellen, dass Redis eingerichtet ist.
* Prüfen Sie das Changelog auf Breaking Changes und Migrationshinweise.
* Abonnieren Sie das öffentliche DockFlare-Agent-Repository, sobald es veröffentlicht ist, um Releases nicht zu verpassen.

Viel Spaß beim Tunnelbau! 🚇
