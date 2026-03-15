# Graceful Deletion verstehen

Wenn Sie einen von DockFlare verwalteten Container stoppen, fällt Ihnen vielleicht auf, dass dessen öffentlicher Hostname nicht sofort offline geht. Dies liegt an einem Feature, das als **Graceful Deletion** (sanftes Löschen) bezeichnet wird.

## Was ist Graceful Deletion?

Anstatt die Cloudflare Ingress-Regel und den DNS-Eintrag in dem Moment augenblicklich zu löschen, in dem ein Container stoppt, markiert DockFlare die Regel als **"pending deletion"** (Löschung ausstehend) und startet einen Timer.

Die zugehörigen Cloudflare-Ressourcen (die Ingress-Regel und der DNS-Eintrag) werden erst dann endgültig gelöscht, wenn dieser Timer, bekannt als **Schonfrist (grace period)**, abläuft.

## Warum ist das nützlich?

Diese Funktion wurde entwickelt, um Dienstunterbrechungen in gängigen operativen Szenarien zu verhindern:

*   **Container-Updates:** Wenn Sie ein Container-Image aktualisieren (`docker compose up -d`), stoppt Docker in der Regel den alten Container und startet einen neuen. Ohne Schonfrist wäre Ihr Dienst für kurze Zeit nicht erreichbar. Bei der Graceful Deletion bleiben der DNS-Eintrag und die Ingress-Regel aktiv, und DockFlare ordnet sie ganz einfach dem neuen Container zu – was zu null Ausfallzeit (Zero Downtime) führt.
*   **Temporäre Neustarts:** Wenn Sie einen Container kurzzeitig anhalten müssen, um eine Einstellung zu ändern und ihn dann neu zu starten, stellt die Schonfrist sicher, dass Ihre öffentlichkeitswirksame Konfiguration intakt bleibt.

## Die Variable `GRACE_PERIOD_SECONDS`

Die Dauer dieser Schonfrist wird durch die Umgebungsvariable `GRACE_PERIOD_SECONDS` gesteuert, die Sie in Ihrer `docker-compose.yml`-Datei festlegen können.

*   Der Standardwert beträgt `600` Sekunden (10 Minuten).
*   Sie können diesen Wert an Ihre Bedürfnisse anpassen. Ein kürzerer Zeitraum beschleunigt die Bereinigung, während ein längerer Zeitraum ein größeres Zeitfenster für Container-Neustarts bietet.

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

1.  **Container gestoppt:** Sie führen `docker stop my-app` aus.
2.  **Löschung ausstehend:** DockFlare erkennt das Stopp-Ereignis. In der Web-UI wird der Status für die Regel von `my-app.example.com` nun als **"pending_deletion"** angezeigt – zusammen mit der Uhrzeit, zu der die Löschung geplant ist.
3.  **Die zwei Szenarien:**
    *   **Szenario A: Schonfrist läuft ab:** Wenn der Container gestoppt bleibt und die Schonfrist (z.B. 10 Minuten) verstreicht, springt DockFlares Hintergrundbereinigung an. Sie löscht die Ingress-Regel aus Ihrem Cloudflare Tunnel und entfernt den CNAME-DNS-Eintrag.
    *   **Szenario B: Container startet neu:** Wenn Sie den Container wieder starten (`docker start my-app`) **bevor** die Schonfrist ausläuft, registriert DockFlare den Start. Es bemerkt, dass die Löschung der Regel aussteht, bricht den Löschvorgang ab und setzt den Status wieder auf **"active"**. Ihr Dienst läuft nahtlos weiter.
