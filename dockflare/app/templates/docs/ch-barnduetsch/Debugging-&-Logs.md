# Debugging & Logs

Wänn du Probleme mit DockFlare beheben, si dini wichtigsten Werkzeuge die vom DockFlare-Container u seinem verwalteten `cloudflared`-Agenten generierten Protokolle (Logs).

## 1. Überprüfung der DockFlare Container-Logs

Die wichtigste Informationsquelle isch die Protokollausgabe des DockFlare-Containers selbst. Diese Logs bieten einen detaillierten Echtzeit-Einblick in das, was DockFlare tut.

### Was du in den Logs finden:
*   Erkennung von Start-/Stopp-Ereignissen der Docker-Container.
*   Verarbeitung von `dockflare.*` Labels.
*   Aufrufe der Cloudflare API.
*   Erfolgsmeldungen oder detaillierte Fehlerantworten von der Cloudflare API.
*   Der Status von Hintergrundaufgaben wie der Ressourcenbereinigung.

### Wie man die Logs anzeigt:
Bruuch den folgenden Docker-Befehl in dim Terminal, um die Protokolle anzuzeigen:
```bash
# View the full log history
docker logs dockflare

# Follow the logs in real-time
docker logs -f dockflare
```

## 2. Nutzung der Web UI Echtzeit-Logs

Der Einfachheit halber enthält das DockFlare-Dashboard einen **Echtzeit-Log-Viewer** am Ende der Hauptseite.

Dieser Viewer streamt genau dieselben Logs, die du mit `docker logs -f dockflare` sehen würden, bietet aber eine einfache Möglichkeit zu sehen, was gerade passiert, ohne dini Browser verlassen zu müesse. Das isch besonders nützlich, um die Aktionen zu beobachten, die DockFlare unmittelbar nach dem Starten oder Stoppen eines Containers ausführt.

## 3. Überprüfung der Logs des `cloudflared`-Agenten

Wänn du vermuetisch, dass das Problem in der Verbindung zwischen dim Server u dem Cloudflare-Netzwerk liegt, chasch die Logs des `cloudflared`-Agenten-Containers direkt überprüfen.

### Wie man die Agenten-Logs anzeigt:
Zuerst muesch den Namen des Agenten-Containers ermitteln. Standardmässig heisst er `cloudflared-agent-<tunnel-name>`, wobei `<tunnel-name>` der Name des in dini DockFlare-Istellige konfigurierten Tunnels isch.

Du chasch den genauen Namen mit `docker ps` herausfinden.

Sobald du de Name hesch, führ us:
```bash
# Replace with the actual container name
docker logs cloudflared-agent-dockflare-tunnel
```

Diese Logs si nützlich für die Diagnose von:
*   Verbindungsfehlern zum Cloudflare-Edge.
*   Authentifizierungsproblemen mit dim Tunnel-Token.
*   Protokollfehlern für den weitergeleiteten Datenverkehr.

**Hinweis:** Das gilt nur, wenn du den standardmässigen **Internen Modus** bruuche. Wänn du den [Externen Modus](External-cloudflared-Mode.md) bruuche, muesch die Logs din eigenen `cloudflared`-Agenten-Prozesses überprüfen.

## 4. Überprüfung des Cloudflare-Dashboards

Vergiss schliesslich nid, das Cloudflare-Dashboard als Diagnosewerkzeug zu nutzen.
*   **DNS-Seite:** Prüef, öb die CNAME-Einträge wie erwartet erstellt wurden.
*   **Zero Trust Dashboard:** Gang zu **Access -> Tunnels**, um den Status din Tunnels u seiner Ingress-Regeln zu überprüfen.
*   **Zero Trust Dashboard:** Gang zu **Access -> Applications**, um die Konfiguration u Integrität dinere Zero Trust-Richtlinien zu kontrollieren. Der "Last Seen" (Zuletzt gesehen)-Status bei Richtlinien cha sehr aufschlussreich sein.
