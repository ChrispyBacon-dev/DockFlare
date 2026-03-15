# DockFlare-Agent u Multi-Server-Architektur

DockFlare 3.0 führt ein verteiltes Ausführungsmodell ein, mit dem du Cloudflare-Tunnel über mehrere Docker-Hosts hinweg verwalten chöi. Der DockFlare **Master** koordiniert die Konfiguration, während leichtgewichtige **Agenten** neben dini Workloads laufen u ihre lokale `cloudflared`-Instanz mit dem Master synchron halten.

Dieser Leitfaden erklärt die Architektur, das Sicherheitsmodell u den schrittweisen Workflow für die Bereitstellige von Agenten.

---

## Warum Agenten?

* **Compute von der Ingress-Steuerung entkoppeln** – halt dini Workloads in der Nähe der Benutzer, während du eine einzige Kontrollebene beibehalten.
* **Sichtbarkeit pro Host** – überwach Heartbeat, Tunnelstatus u Befehlshistorie für jeden Agenten.
* **Token mit geringsten Rechten** – kompromittierte Agenten chöi widerrufen wärde, ohne den Master oder andere Hosts anzutasten.
* **Erhöhte Ausfallsicherheit** – Agenten bedienen den Verkehr weiterhin mit ihrer zuletzt bekannten Konfiguration, wenn der Master vorübergehend nid erreichbar sein sollte.

---

## Komponenten im Überblick

| Komponente | Verantwortlichkeit |
|-----------|----------------|
| **Master (DockFlare)** | Hostet die Web UI, speichert den Status, gleicht gewünschte Ingress-Regeln ab u erteilt Befehle. |
| **Redis** | Backplane für Caching, Agenten-Heartbeats u anstehende Befehle in der Warteschlange. |
| **DockFlare Agent** | Headless-Container, der lokale Docker-Ereignisse beobachtet, Befehle ausführt u `cloudflared` betreibt. |
| **cloudflared** | Behandelt die eigentliche Tunnelverbindung zu Cloudflare pro Agent. |

Master u Redis laufen typischerweise zusammen, während Agenten neben Workloads laufen (möglicherweise in anderen Netzwerken).

---

## Voraussetzige

* DockFlare Master ≥ v3.0 mit konfiguriertem Redis (`REDIS_URL` gesetzt). Optional chasch `REDIS_DB_INDEX` festlegen, um Daten von anderen Containern zu isolieren, die dieselbe Redis-Instanz bruuche.
* Cloudflare API-Token mit Tunnel- + Access-Berechtigungen (gleich wie in früheren Versionen).
* Docker-Laufzeit auf jedem Host, den du verwalten wotsch.
* (Optional) Spezielles Netzwerksegment oder VPN zwischen Master u Agenten, wenn du den Master nid öffentlich zugänglich machen.

---

## Workflow-Überblick

1. **Agenten-API-Schlüssel generieren** in der DockFlare UI (`Agents → Generate Key`).
2. **DockFlare Agent-Container ausrollen** auf dem Remote-Host, wobei Master-URL u Schlüssel übergeben wärde.
3. Der Agent **registriert** sich beim Master u erscheint mit dem Status *Ausstehend (Pending)*.
4. In der Master-UI **enrol den Agenten** (freischalten) – wiis ihm einen Cloudflare Tunnel zu oder erstell einen neuen Tunnel für diesen Host.
5. Der Master reiht Befehle ein; der Agent **ruft diese ab (polls)**, wendet die Konfiguration an u meldet Status/Heartbeat. DockFlare erkennt die Zielzone für jeden Hostnamen automatisch (u fällt nur auf die Standardzone zurück, wenn die Erkennung fehlschlägt).
6. Wenn Container auf dem Host des Agenten gestartet oder gestoppt wärde, streamt der Agent Ereignisse an den Master zurück, der wiederum DNS, Zugriffsrichtlinien u Tunnel-Eingangsregeln aktualisiert.

---

## Bereitstellige des DockFlare Agenten

> ℹ️ Der Agent wird als `alplat/dockflare-agent` veröffentlicht. Solange das öffentliche Repository noch nid online isch, chasch ihn aus dem `DockFlare-agent` Source-Tree erstellen, der in DockFlare 3.0 enthalten isch.

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

- Führ `docker network create cloudflare-net` einmal aus, um das gemeinsame Netzwerk für Master u Agenten bereitzustellen.
- Der Socket-Proxy begrenzt die Docker-API-Oberfläche, die der Agent erreichen cha; nur die auf `1` gesetzten Fähigkeiten si erreichbar.
- Das Agenten-Image läuft als unprivilegierte `dockflare`-Benutzer (UID/GID 65532). lueg dass gemounteti Verzeichnisse wie `/app/data` für dä User schriibbar si, oder bau s'Image so, dass es zu dine Host-Berechtige passt.
- Füll eine `.env`-Datei mit `DOCKFLARE_MASTER_URL` u `DOCKFLARE_API_KEY` aus; optionale Overrides (zum Biispil `LOG_LEVEL` oder `DOCKER_HOST`) chasch auf die gleiche Weise setzen.

---

## Sicherheitsmodell

* **Master API Key** – schützt d'administrativi API. D'UI zeigt ne erscht a, nachdem du uf *Show master API key* klickt hesch.
* **Agent API Keys** – eindeutig pro Agent. Ein Widerruf sperrt sofort weitere Registrierungen u Befehle von diesem Host.
* **Redis** – wird für Queues u Caches verwendet; sicher dr Redis ab (Passwort + Network ACLs), wänn er ausserhalb vo mene vertrouenswürdige LAN lauft.
* **Transport** – betriib den Master hinter HTTPS (zum Biispil via Cloudflare Access), damit der Agent-Traffic verschlüsselt isch.
* **Least-Privilege Runtime** – der Agent-Container läuft als `dockflare`-User (UID/GID 65532) u verwendet den Socket-Proxy, um Docker-Zugriff auf Container-Inspection u Lifecycle-Operationen zu begrenzen.

### Empfohlene Härtung

1. Bhalt Agent Keys in einem Vault/Passwortmanager auf u rotier sie regelmässig.
2. **Deaktivier das Passwort-Login nid**: Bruuch stattdessen OAuth/OIDC-Anbieter für SSO, ohne Sicherheitsrisiken zu erzeugen. Wänn du Passwort-Login unbedingt deaktivieren müesse, beacht, dass Container im selben Docker-Netzwerk externe Authentifizierung umgehen u direkt auf die DockFlare-API zugreifen chöi. Details siehe [Zugriff auf die Web UI](Accessing-the-Web-UI.md).
3. Bruuch nach Möglichkeit einen eigenen Tunnel pro Agent, um Privilegien sauber zu isolieren.
4. Überwach in der UI unter `Agents` Heartbeat-Lücken; offline Nodes chöi direkt aus der UI entfernt wärde.

---

## Problem löse

| Symptom | Lösung |
|---------|--------|
| Agent bleibt in `pending` | lueg dass er mit dem richtigen API Key registriert isch, u enrol ihn in der UI. |
| Commands wärde nie abgearbeitet | Prüef die Redis-Konnektivität u dass die Container-Uhren (Clock) synchron si. |
| DNS wird nid aktualisiert | Der Master mues Cloudflare erreichen chöi u der Agent mues Container-Events senden; prüef `docker logs dockflare-agent`. |
| Heartbeat isch offline | Prüef den Network Path zwischen Agent u Master; häufige Ursachen si Firewall- oder TLS-Probleme. |

---

## Nächste Schritte

* Lueg dr aktualisiert Schnellstart im README aa, demit du sicher bisch dass Redis iigrichtet isch.
* Prüef das Changelog auf Breaking Changes u Migrationshinweise.
* Abonnier das öffentliche DockFlare-Agent-Repository, sobald es veröffentlicht isch, um Releases nid zu verpassen.

Viu Spass bim Tunnelbaue.
