# Graceful Deletion verstehen

Wänn du einen von DockFlare verwalteten Container stoppen, fällt dir vielleicht auf, dass dessen öffentlicher Hostname nid sofort offline geht. Das liegt an einem Feature, das als **Graceful Deletion** (sanftes Löschen) bezeichnet wird.

## Was isch Graceful Deletion?

Anstatt die Cloudflare Ingress-Regel u den DNS-Eintrag in dem Moment augenblicklich zu löschen, in dem ein Container stoppt, markiert DockFlare die Regel als **"pending deletion"** (Löschung ausstehend) u startet einen Timer.

Die zugehörigen Cloudflare-Ressourcen (die Ingress-Regel u der DNS-Eintrag) wärde erst dann endgültig gelöscht, wenn dieser Timer, bekannt als **Schonfrist (grace period)**, abläuft.

## Warum isch das nützlich?

Diese Funktion wurde entwickelt, um Dienstunterbrechungen in gängigen operativen Szenarien zu verhindern:

*   **Container-Updates:** Wänn du ein Container-Image aktualisieren (`docker compose up -d`), stoppt Docker in der Regel den alten Container u startet einen neuen. Ohne Schonfrist wäre din Dienst für kurze Zeit nid erreichbar. Bei der Graceful Deletion bleiben der DNS-Eintrag u die Ingress-Regel aktiv, u DockFlare ordnet sie ganz einfach dem neuen Container zu – was zu null Ausfallzeit (Zero Downtime) führt.
*   **Temporäre Neustarts:** Wänn du einen Container kurzzeitig anhalten müesse, um eine Istellige zu ändern u ihn dann neu zu starten, stellt die Schonfrist sicher, dass dini öffentlichkeitswirksame Konfiguration intakt bleibt.

## Die Variable `GRACE_PERIOD_SECONDS`

Die Dauer dieser Schonfrist wird durch die Umgebungsvariable `GRACE_PERIOD_SECONDS` gesteuert, die du in dinere `docker-compose.yml`-Datei festlegen chöi.

*   Der Standardwert beträgt `600` Sekunden (10 Minuten).
*   du chasch diesen Wert an dini Bedürfnisse anpassen. Ein kürzerer Zeitraum beschleunigt die Bereinigung, während ein längerer Zeitraum ein grösseres Zeitfenster für Container-Neustarts bietet.

**Beispiel:**
```yaml
services:
  dockflare:
    image: alplat/dockflare:stable
    # ... other settings
    environment:
      - GRACE_PERIOD_SECONDS=3600 # Set a 1-hour grace period
```

## Wie es in der Praxis funktioniert

1.  **Container gestoppt:** du führen `docker stop my-app` aus.
2.  **Löschung ausstehend:** DockFlare erkennt das Stopp-Ereignis. In der Web UI wird der Status für die Regel von `my-app.example.com` nun als **"pending_deletion"** angezeigt – zusammen mit der Uhrzeit, zu der die Löschung geplant isch.
3.  **Die zwei Szenarien:**
    *   **Szenario A: Schonfrist läuft ab:** Wenn der Container gestoppt bleibt u die Schonfrist (z.B. 10 Minuten) verstreicht, springt DockFlares Hintergrundbereinigung an. Du löscht die Ingress-Regel aus dim Cloudflare Tunnel u entfernt den CNAME-DNS-Eintrag.
    *   **Szenario B: Container startet neu:** Wänn du den Container wieder starten (`docker start my-app`) **bevor** die Schonfrist ausläuft, registriert DockFlare den Start. Es bemerkt, dass die Löschung der Regel aussteht, bricht den Löschvorgang ab u setzt den Status wieder auf **"active"**. din Dienst läuft nahtlos weiter.
