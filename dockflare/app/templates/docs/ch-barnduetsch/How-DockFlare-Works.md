# Wie DockFlare funktioniert

DockFlare isch d Brugg zwüsche dim Docker-Host u Cloudflare. Es lost uf Container-Änderige, wertet d `dockflare.*`-Labels uus u verwaltet in dim Name Tunnel, DNS-Iiträg u Access-Richtlinie.

## Grundablouf

Im Grundsatz lauft s so:

1. **Docker-Ereignis überwachä:** DockFlare lost uf `start`, `stop` u angeri Container-Events.

2. **Labels uswerte:** Wänn e Container startet, prüeft DockFlare d `dockflare.*`-Labels. Mit `dockflare.enable=true` weiss es, dass dä Container verwaltet söll wärde.

3. **Cloudflare aktualisiere:** Usgangslage si d Labels. DockFlare legt drus a:
   * **Tunnel-Ingress-Regle**
   * **DNS-CNAME-Iiträg**
   * **Access-Richtlinie oder Access Groups**

4. **Automatisch ufruume:** Wänn e verwaltete Container stoppt oder usefliegt, räumt DockFlare Ingress-Regle, DNS-Iiträg u Access-Ressource wieder uf, sofern nüt angers dä Hostname no bruucht.

## Komponente im Überblick

| Komponente | Verantwortlichkeit |
| --- | --- |
| DockFlare Master | Hostet UI u API, lost uf Docker-Events u steuert Tunnel, DNS u Access. |
| Docker Socket Proxy | Git em Master nume die Docker-API-Teili frei, wo er würklech bruucht. |
| Redis | Bruucht DockFlare für Cache, Queue, Log-Streaming u Agenten-Backchannel. |
| DockFlare Agents (optional) | Läufe uf wytete Hosts u verwalte dört ihr eigets `cloudflared`. |
| `cloudflared` | Baut d Verbindig zu Cloudflare ufrecht. |

## Mehschichtigs Konfigurationsmodell

DockFlare kombiniert Automatisierig mit manueller Kontroll:

1. **Docker-Labels:** D Basis u dr Standardfall. Hie definierisch Hostname, Service-URL u Sicherheit.

2. **Access Groups:** Wiederverwendbari Vorlag für Zugriffsregle, wo du i dr Web UI einisch aaleisch u nachhär per Label zuedotisch.

3. **Web UI-Overrides:** D Web UI git dir d höchscht Kontroll. Du chasch dort Policies überschrybe, manuelle Regle aalege oder e Dienst wieder uf dr Label-Stand zrüggsetze.

So chasch s meischte per Label automatisiere u gliich Spezialfäll i dr Web UI löse.

---

## Architektur der Access-Richtlinien (v3.0.3+)

### Wiederverwendbares Richtliniensystem

DockFlare verwendet jetzt eine **wiederverwendbare Richtlinienarchitektur**, die sich an den Best Practices von Cloudflare orientiert:

1. **Access Groups** → synchronisieren mit → **Cloudflare Reusable Policies**
2. **Access Applications** → referenzieren → **Reusable Policy IDs**
3. **Eine einzige Quelle der Wahrheit** → einmal aktualisieren, überall anwenden

Diese Architektur vermeidet doppelte Richtlinien u ermöglicht die Verwaltig sowohl über DockFlare als auch über das Cloudflare-Dashboard mit vollständiger bidirektionaler Synchronisierung.

### Systemverwaltete Richtlinien

DockFlare verwaltet zwei zentrale Richtlinien automatisch, um konsistentes Verhalten sicherzustellen:

- **`public-default-bypass`**: Richtlinie für öffentlichen Zugriff per Bypass
  - Nicht löschbare Systemrichtlinie
  - Wird bei der Initialisierung automatisch erstellt
  - Cloudflare-Name: `DockFlare-Default-Public-Access-Bypass`
  - Entscheidung: `bypass` mit Einschlussregel `everyone`
  - Wird von allen Diensten verwendet, die öffentlichen Zugriff ohne Zonenschutz benötigen
  - Verhindert doppelte Bypass-Richtlinien im Cloudflare-Dashboard

- **`authenticated-default`**: Standardrichtlinie für Authentifizierung
  - Nicht löschbare Systemrichtlinie
  - Wird bei der Initialisierung automatisch erstellt
  - Cloudflare-Name: `DockFlare-Default-Authenticated-Access`
  - Entscheidung: `allow` mit Einmal-PIN u E-Mail-Beschränkung
  - Wird für grundlegende Szenarien mit authentifiziertem Zugriff verwendet

### Migration älterer Labels

DockFlare migriert ältere Labels automatisch auf Systemrichtlinien:

- `dockflare.access.policy=bypass` → verwendet `public-default-bypass`
- `dockflare.access.group=bypass` → verwendet `public-default-bypass`
- `dockflare.access.policy=authenticate` → verwendet `authenticated-default`

D'Migration lauft im Hingergrund während der Verarbeitung u des Abgleichs von Containern. Du muesch nüt von Hand mache.

### Zonen-Standardrichtlinien

Wildcard-Richtlinien auf Zonenebene (`*.domain.com`) sorgen über die Priorität von Richtlinien für mehrschichtige Sicherheit:

1. **Spezifische Hostnamen-Richtlinie** (zum Biispil `app.example.com`) - höchste Priorität
2. **Zonen-Wildcard-Richtlinie** (zum Biispil `*.example.com`) - Fallback
3. **Keine Richtlinie** = öffentlicher Zugriff ohne Access App - Standardverhalten

So wird sichergestellt, dass auch vergessene oder nid dokumentierte Dienste weiterhin durch die Richtlinie auf Zonenebene geschützt bleiben.

**Beispiel:**
- Zonenrichtlinie: `*.internal.company.com` → erfordert Authentifizierung über Firmen-E-Mail
- Spezifischer Dienst: `public-demo.internal.company.com` → verwendet `public-default-bypass`
- Vergessener Dienst: `test.internal.company.com` → bleibt durch die Zonenrichtlinie geschützt u erfordert Authentifizierung
