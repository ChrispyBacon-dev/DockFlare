# DockFlare-Agent u Multi-Server-Architektur

Mit DockFlare 3.0 chasch Cloudflare-Tunnel über mehri Docker-Hosts verwalte. Dr **Master** übernimmt d Steuerig, während liechti **Agente** neb de Workloads loufe u ihri lokal `cloudflared`-Instanz mit em Master synchron halte.

Die Aaleitig erklärt Architektur, Sicherheitsmodell u dr typische Ablauf für d Bereitstellig vo Agente.

---

## Warum Agente?

* **Compute u Ingress-Steuerig trenne** – Dini Workloads chöi nöcher bi de Benutzer laufe, während d Steuerig zentral blybt.
* **Sichtbarkeit pro Host** – Du gsehsch Heartbeat, Tunnelstatus u Befehlsverlauf pro Agent.
* **Token mit wenig Rächte** – Kompromittierti Agente chöi einzelni widerruefe wärde, ohni dr Master oder angeri Hosts z tangiere.
* **Besseri Uusfallsicherhäit** – Wänn dr Master churz offline isch, chöi Agente mit dr letschte bekannte Konfiguration wyterloufe.

---

## Komponente im Überblick

| Komponente | Ufgaab |
|-----------|--------|
| **Master (DockFlare)** | Hostet d Web UI, speichert dr Status, gleicht d Soll-Konfiguration ab u schickt Befähl an d Agente. |
| **Redis** | Backplane für Cache, Agent-Heartbeats u wartendi Befähl. |
| **DockFlare Agent** | Headless-Container, wo lokal Docker-Events überwacht, Befähl usführt u `cloudflared` betreibt. |
| **cloudflared** | Baut pro Agent d eigentlechi Tunnelverbindig zu Cloudflare uuf. |

Meischt loufe Master u Redis zäme, während d Agente bi de Workloads platziert sy, je nach Fall ou in angerne Netzwerch.

---

## Voraussetzige

* DockFlare Master ab v3.0 mit konfiguriertem Redis (`REDIS_URL` gsetzt)
* E Cloudflare API-Token mit Tunnel- u Access-Rächt
* E Docker-Runtime uf jedem Host, wo du verwalte wotsch
* Optional es separates Netz oder VPN zwüsche Master u Agent, wänn dr Master nid öffentlich söll sy

---

## Typische Ablauf

1. I dr DockFlare UI e **Agenten-API-Schlüssu** generiere (`Agents → Generate Key`)
2. Dr **DockFlare-Agent-Container** uf em Zielhost usrolle u Master-URL plus API-Schlüssu übergäh
3. Dr Agent **registriert** sech bim Master u erscheint mit em Status *Pending*
4. I dr Master-UI dr Agent **freischalte** u ihm e Cloudflare-Tunnel zuewyse oder grad e nöie erstelle
5. Dr Master stellt Befähl i d Warteschlange; dr Agent holt si ab, setzt d Konfiguration um u meldet Status u Heartbeat zrügg
6. Wänn uf em Agent-Host Container starte oder stoppe, streamt dr Agent d Ereignis zrügg a dr Master, wo DNS, Access-Richtlinie u Tunnel-Ingress aktualisiert

---

## DockFlare Agent deploye

> ℹ️ Dr Agent wird als `alplat/dockflare-agent` publiziert. Solang ds öffentleche Repository no nid online isch, chasch ihn us em `DockFlare-agent`-Source-Tree boue, wo i DockFlare 3.0 drbi isch.

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

Minimali `docker-compose.yml` uf em Agent-Host:

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

* Führ `docker network create cloudflare-net` einisch uus, zum s gmeinsame Netz für Master u Agente bereitzstelle.
* Dr Socket-Proxy schränkt d Docker-API i uf genau die Fähigkeite, wo dr Agent würklech brucht.
* S Agent-Image louft als unprivilegierte Benutzer `dockflare` (UID/GID 65532). Lueg, dass gemounteti Verzeichnis wie `/app/data` für dä User schriibbar sy, oder bau s Image mit passende UID/GID neu.
* Füll e `.env`-Datei mit `DOCKFLARE_MASTER_URL` u `DOCKFLARE_API_KEY`; optional chasch `LOG_LEVEL` oder `DOCKER_HOST` genau glych überschrybe.

---

## Sicherheitsmodell

* **Master API Key** – schützt d administrativi API. I dr UI wird er ersch azeigt, wänn du uf *Show master API key* klicksch.
* **Agent API Keys** – pro Agent eindeutig. E Widerruef sperrt wiiteri Registrierige u Befähl vo däm Host sofort.
* **Redis** – wird für Queue u Cache bruucht; sicher Redis ab, vor allem wänn er usserhalb vo dim vertrouenswürdige Netz lauft.
* **Transport** – Betriib dr Master hinder HTTPS, zum Bispil mit Cloudflare Access, damit dr Agent-Traffic verschlüsslet isch.
* **Least-Privilege Runtime** – Dr Agent-Container louft als `dockflare`-User (UID/GID 65532) u bruucht e Socket-Proxy, damit dr Docker-Zuegriff uf ds Nötigste beschränkt blybt.

### Empfohlni Härtig

1. Agent-Keys i mene Vault oder Passwortmanager ufbewahre u regelmässig rotiere
2. Wenn möglich pro Agent e eigete Tunnel bruuche, zum d Privilegie sauber z trenne
3. I dr UI under `Agents` Heartbeat-Lücke beobachte; offline Hosts chöi diräkt entfernt wärde
4. Für d Master-UI lieber OAuth/OIDC oder e guet abgesicherte Passwort-Aamäldig statt riskanti Netzwerch-Abchürzige

---

## Problem löse

| Symptom | Lösig |
|---------|-------|
| Agent blybt uf `pending` | Prüef, ob dr richtig API-Key verwendet wird, u schalt dr Agent i dr UI frei. |
| Commands wärde nie abgschafft | Prüef d Redis-Verbindig u lueg, dass d Container-Uhre synchron sy. |
| DNS wird nid aktualisiert | Dr Master muess Cloudflare erreiche chönne, u dr Agent muess Container-Events zrüggschicke; prüef `docker logs dockflare-agent`. |
| Heartbeat isch offline | Prüef d Verbindig zwüsche Agent u Master; tüüfischi Ursach sy oft Firewall- oder TLS-Problem. |

---

## Nächschti Schritt

* Lueg dr aktualisiert Schnellstart im README aa, zum sicher z sy, dass Redis sauber iigrichtet isch
* Prüef ds Changelog uf Breaking Changes u Migrationshinwys
* Beobacht ds öffentliche DockFlare-Agent-Repository, sobald es veröffentlecht isch, damit du Releases nid verpassisch

Viu Spass bim Tunnelbaue.
