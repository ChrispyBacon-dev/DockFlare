# Debugging & Logs

Wenn Sie Probleme mit DockFlare beheben, sind Ihre wichtigsten Werkzeuge die vom DockFlare-Container und seinem verwalteten `cloudflared`-Agenten generierten Protokolle (Logs).

## 1. Überprüfung der DockFlare Container-Logs

Die wichtigste Informationsquelle ist die Protokollausgabe des DockFlare-Containers selbst. Diese Logs bieten einen detaillierten Echtzeit-Einblick in das, was DockFlare tut.

### Was Sie in den Logs finden:
*   Erkennung von Start-/Stopp-Ereignissen der Docker-Container.
*   Verarbeitung von `dockflare.*` Labels.
*   Aufrufe der Cloudflare API.
*   Erfolgsmeldungen oder detaillierte Fehlerantworten von der Cloudflare API.
*   Der Status von Hintergrundaufgaben wie der Ressourcenbereinigung.

### Wie man die Logs anzeigt:
Verwenden Sie den folgenden Docker-Befehl in Ihrem Terminal, um die Protokolle anzuzeigen:
```bash
# View the full log history
docker logs dockflare

# Follow the logs in real-time
docker logs -f dockflare
```

## 2. Nutzung der Web-UI Echtzeit-Logs

Der Einfachheit halber enthält das DockFlare-Dashboard einen **Echtzeit-Log-Viewer** am Ende der Hauptseite.

Dieser Viewer streamt genau dieselben Logs, die Sie mit `docker logs -f dockflare` sehen würden, bietet aber eine einfache Möglichkeit zu sehen, was gerade passiert, ohne Ihren Browser verlassen zu müssen. Dies ist besonders nützlich, um die Aktionen zu beobachten, die DockFlare unmittelbar nach dem Starten oder Stoppen eines Containers ausführt.

## 3. Überprüfung der Logs des `cloudflared`-Agenten

Wenn Sie vermuten, dass das Problem in der Verbindung zwischen Ihrem Server und dem Cloudflare-Netzwerk liegt, können Sie die Logs des `cloudflared`-Agenten-Containers direkt überprüfen.

### Wie man die Agenten-Logs anzeigt:
Zuerst müssen Sie den Namen des Agenten-Containers ermitteln. Standardmäßig heißt er `cloudflared-agent-<tunnel-name>`, wobei `<tunnel-name>` der Name des in Ihren DockFlare-Einstellungen konfigurierten Tunnels ist.

Sie können den genauen Namen mit `docker ps` herausfinden.

Sobald Sie den Namen haben, führen Sie aus:
```bash
# Replace with the actual container name
docker logs cloudflared-agent-dockflare-tunnel
```

Diese Logs sind nützlich für die Diagnose von:
*   Verbindungsfehlern zum Cloudflare-Edge.
*   Authentifizierungsproblemen mit Ihrem Tunnel-Token.
*   Protokollfehlern für den weitergeleiteten Datenverkehr.

**Hinweis:** Dies gilt nur, wenn Sie den standardmäßigen **Internen Modus** verwenden. Falls Sie den [Externen Modus](External-cloudflared-Mode.md) verwenden, müssen Sie die Logs Ihres eigenen `cloudflared`-Agenten-Prozesses überprüfen.

## 4. Überprüfung des Cloudflare-Dashboards

Vergessen Sie schließlich nicht, das Cloudflare-Dashboard als Diagnosewerkzeug zu nutzen.
*   **DNS-Seite:** Prüfen Sie, ob die CNAME-Einträge wie erwartet erstellt wurden.
*   **Zero Trust Dashboard:** Gehen Sie zu **Access -> Tunnels**, um den Status Ihres Tunnels und seiner Ingress-Regeln zu überprüfen.
*   **Zero Trust Dashboard:** Gehen Sie zu **Access -> Applications**, um die Konfiguration und Integrität Ihrer Zero Trust-Richtlinien zu kontrollieren. Der "Last Seen" (Zuletzt gesehen)-Status bei Richtlinien kann sehr aufschlussreich sein.
