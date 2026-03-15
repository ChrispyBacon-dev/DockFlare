# Interner vs. Externer `cloudflared`

DockFlare kann in zwei Modi betrieben werden, um den `cloudflared`-Agenten zu verwalten, also die Softwarekomponente, die tatsächlich die dauerhafte Verbindung zwischen Ihrem Server und dem Cloudflare-Netzwerk herstellt. Das Verständnis dieser beiden Modi ist entscheidend für die Wahl des richtigen Setups für Ihre Umgebung.

## Interner Modus (Standard)

Im internen Modus übernimmt DockFlare die volle Verantwortung für die Verwaltung des `cloudflared`-Agenten.

### Wie es funktioniert
Wenn DockFlare startet, wird es automatisch:
1.  Einen eigenen Docker-Container erstellen, auf dem das `cloudflare/cloudflared`-Image läuft.
2.  Diesen Agenten-Container konfigurieren, um sich mit Ihrem Cloudflare-Konto zu verbinden und den in Ihren DockFlare-Einstellungen angegebenen Tunnel zu verwenden.
3.  Sicherstellen, dass der Agent läuft, und ihn im Fehlerfall neu starten.
4.  Automatisch alle relevanten Einstellungen anwenden, wie z.B. die Aktivierung des Prometheus-Metrik-Endpunkts.

Dies ist der **Standard- und empfohlene** Modus für die meisten Benutzer.

### Vorteile
*   **Einfachheit:** Es ist eine "Zero-Configuration"-Einrichtung. DockFlare übernimmt alles für Sie.
*   **Garantierte Kompatibilität:** DockFlare stellt sicher, dass der Agent so konfiguriert ist, wie er damit arbeiten kann.
*   **Zentrale Verwaltung:** Alles, was mit Ihren Tunneln zu tun hat, wird von DockFlare verwaltet.

### Nachteile
*   **Weniger Kontrolle:** Sie haben nur eingeschränkte Kontrolle über die Konfiguration des `cloudflared`-Agenten, abseits dessen, was DockFlare offenlegt.

---

## Externer `cloudflared` Modus

Im externen Modus sind Sie selbst für den Betrieb und die Verwaltung des `cloudflared`-Agenten verantwortlich. DockFlare verbindet sich mit diesem bestehenden Agenten, anstatt einen eigenen zu erstellen.

### Wie es funktioniert
DockFlare wird **keinen** `cloudflared`-Container erstellen. Stattdessen geht es davon aus, dass irgendwo ein `cloudflared`-Agent läuft, den es verwenden kann. Dies könnte sein:
*   Ein `cloudflared`-Prozess, der direkt auf dem Host-Betriebssystem läuft (z.B. als `systemd`-Dienst).
*   Ein `cloudflared`-Container, den Sie selbst mit einer separaten `docker-compose.yml`-Datei oder einem Docker-Run-Befehl verwalten.
*   Ein `cloudflared`-Agent, der auf einer komplett anderen Maschine läuft.

Dies ist ein **fortgeschrittener Modus**, der für Benutzer mit spezifischen Anforderungen oder komplexen bestehenden Setups gedacht ist.

### Vorteile
*   **Maximale Kontrolle:** Sie haben die volle Kontrolle über den `cloudflared`-Agenten, einschließlich seiner Version, Kommandozeilenargumente und seines Lebenszyklus.
*   **Integration in bestehende Setups:** Perfekt, wenn bereits ein `cloudflared`-Agent für andere Zwecke bei Ihnen läuft.
*   **Entkopplung:** Entkoppelt den Lebenszyklus von DockFlare vom Lebenszyklus des `cloudflared`-Agenten.

### Nachteile
*   **Komplexität:** Sie sind dafür verantwortlich, sicherzustellen, dass der `cloudflared`-Agent läuft, richtig konfiguriert und mit dem richtigen Tunnel verbunden ist.
*   **Konfigurationsaufwand:** Sie müssen DockFlare konfigurieren, um diesen externen Agenten zu nutzen.

### So aktivieren Sie den externen Modus
Um den externen Modus zu aktivieren, müssen Sie die folgenden Umgebungsvariablen für den DockFlare-Container setzen:

*   `USE_EXTERNAL_CLOUDFLARED=true`: Aktiviert den externen Modus.
*   `EXTERNAL_TUNNEL_ID`: Muss auf die UUID des Tunnels gesetzt werden, auf die Ihr externer `cloudflared`-Agent konfiguriert ist.

Wenn diese Variablen gesetzt sind, überspringt DockFlare die interne Agentenverwaltung und sendet stattdessen alle Ingress-Regelkonfigurationen an den Tunnel, der durch `EXTERNAL_TUNNEL_ID` angegeben ist.
