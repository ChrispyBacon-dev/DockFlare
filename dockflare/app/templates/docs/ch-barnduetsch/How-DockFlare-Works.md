# Wie DockFlare funktioniert

DockFlare fungiert als Brücke zwischen dinere Docker-Umgebung u dem Cloudflare-Netzwerk u automatisiert die sichere Veröffentlichung von Diensten im Internet. Es überwacht dini Docker-Host kontinuierlich u nutzt die Cloudflare-API, um Tunnel, DNS-Einträge u Access-Richtlinien in dim Namen zu verwalten.

## Kern-Workflow

Der grundlegende Ablauf lässt sich in einige zentrale Schritte aufteilen:

1. **Überwachung von Docker-Ereignissen**: DockFlare lauscht auf Ereignisse des Docker-Sockets, etwa `start` u `stop` von Containern.

2. **Erkennung von Labels**: Wenn ein neuer Container startet, prüft DockFlare, öb `dockflare.`-Labels vorhanden si. Findet es `dockflare.enable=true`, weiss DockFlare, dass dieser Container verwaltet wärde soll.

3. **Interaktion mit der Cloudflare-API**: Auf Basis dieser Labels konfiguriert DockFlare die benötigten Ressourcen in Cloudflare:
   * **Cloudflare Tunnel**: DockFlare fügt dem vorgesehenen Cloudflare-Tunnel eine Ingress-Regel hinzu. Diese Regel verweist den öffentlichen Hostnamen auf die interne Netzwerkadresse des Containers, zum Biispil `http://my-app:8080`.
   * **DNS-Verwaltung**: DockFlare erstellt einen CNAME-Eintrag in dinere Cloudflare-DNS-Zone u verweist damit den gewünschten öffentlichen Hostnamen, etwa `my-app.example.com`, auf dini Cloudflare-Tunnel.
   * **Access-Richtlinien**: Wenn Zugriffskontroll-Labels gesetzt wurden, erstellt oder aktualisiert DockFlare eine wiederverwendbare Cloudflare-Access-Richtlinie, um den Dienst mit Zero-Trust-Regeln abzusichern, zum Biispil durch Anmeldung über einen Identitätsanbieter oder durch einen öffentlichen `bypass`.

4. **Automatische Bereinigung**: Wenn ein verwalteter Container gestoppt oder entfernt wird, startet DockFlare automatisch einen Cleanup-Prozess. Die zugehörige Ingress-Regel wird aus dem Cloudflare-Tunnel entfernt. Falls kei anderer Dienst denselben Hostnamen verwendet, löscht DockFlare zusätzlich den DNS-Eintrag u die Access Application. Dadurch bleiben kener veralteten Einträge zurück u dini Cloudflare-Konfiguration bleibt sauber.

## Komponenten im Überblick

| Komponente | Verantwortlichkeit |
| --- | --- |
| DockFlare Master | Hostet UI u API, überwacht Docker-Ereignisse u orchestriert Cloudflare-Tunnel, DNS u Access-Richtlinien. Läuft rootless u kommuniziert nur über den Socket-Proxy mit Docker. |
| Docker Socket Proxy | `tecnativa/docker-socket-proxy`-Sidecar, das dem Master nur die minimale Docker-API-Oberfläche (`containers`, `events` usw.) bereitstellt. So wird verhindert, dass der Master den rohen Docker-Socket direkt bindet. |
| Redis | Zuständig für Caching, Warteschlangen, Log-Streaming u den Heartbeat-/Backchannel der Agenten. Läuft im privaten Netzwerk `dockflare-internal`. |
| DockFlare Agents (optional) | Remote-Prozesse, die das Verhalten des Masters auf anderen Hosts nachbilden, Docker-Ereignisse zurückstreamen u ihr eigenes `cloudflared` verwalten. |
| `cloudflared` | Hält die Tunnelverbindung zu Cloudflare entweder für den Master oder für jeden Agenten aufrecht. |

## Mehrschichtiges Konfigurationsmodell

DockFlare verwendet einen flexiblen, mehrschichtigen Konfigurationsansatz, der Automatisierung u feingranulare Kontrolle kombiniert:

1. **Docker-Labels (Basisschicht)**: Das isch die primäre, automatisierte Methode. Du definierisch die vollständige Konfiguration eines Dienstes, also Hostname, interne Dienst-URL u Zugriffsrichtlinie, direkt in dinere `docker-compose.yml` oder im Docker-Run-Befehl. Diese Angaben si die massgebliche Quelle für automatisierte Dienste.

2. **Access Groups (Abstraktionsschicht)**: Damit komplexe Zugriffsrichtlinien nid für viele Dienste wiederholt wärde müesse, chasch in der Web UI wiederverwendbare **Access Groups** anlegen. Diese Vorlagen bündeln Regeln wie „Firmen-E-Mails zulassen“ oder „Zugriff aus bestimmten Ländern erlauben“ u synchronisieren diese mit benannten, wiederverwendbaren Cloudflare-Access-Richtlinien. Der Umschalter „Public vs Authenticated“ im Dialog legt fest, öb DockFlare ein `bypass` oder `allow` erzeugt. So cha eine gesamte Richtlinie mit nur einem Label wie `dockflare.access.group=my-policy-group` auf einen Container angewendet wärde.

3. **Web UI-Overrides (Kontrollschicht)**: Die Web UI bietet die höchste Kontrolle. Über das Dashboard chasch:
   * die Access-Richtlinie eines Dienstes **überschreiben**, unabhängig davon, öb sie ursprünglich per Label oder Access Group definiert wurde. Diese Overrides bleiben auch nach einem Neustart des Containers bestehen.
   * **manuelle Ingress-Regeln** für Dienste anlegen, die nid in Docker laufen, zum Biispil für einen Dienst auf einem anderen Rechner im Netzwerk.
   * die Konfiguration eines Dienstes **auf den Stand der Docker-Labels zurücksetzen** u dabei alle in der UI vorgenommenen Overrides verwerfen.

Das Modell erlaubt es, die meisten Dienste per Docker-Label nach dem Prinzip „einrichten u laufen lassen“ zu automatisieren, ohne auf die Möglichkeit zu verzichten, Ausnahmen u komplexere Szenarien über die Web UI zu steuern.

---

## Architektur der Access-Richtlinien (v3.0.3+)

### Wiederverwendbares Richtliniensystem

DockFlare verwendet jetzt eine **wiederverwendbare Richtlinienarchitektur**, die sich an den Best Practices von Cloudflare orientiert:

1. **Access Groups** → synchronisieren mit → **Cloudflare Reusable Policies**
2. **Access Applications** → referenzieren → **Reusable Policy IDs**
3. **Eine einzige Quelle der Wahrheit** → einmal aktualisieren, überall anwenden

Diese Architektur vermeidet doppelte Richtlinien u ermöglicht die Verwaltung sowohl über DockFlare als auch über das Cloudflare-Dashboard mit vollständiger bidirektionaler Synchronisierung.

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
