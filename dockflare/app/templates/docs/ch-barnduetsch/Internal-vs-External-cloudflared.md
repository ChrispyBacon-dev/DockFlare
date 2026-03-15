# Interner vs. Externer `cloudflared`

DockFlare cha in zwei Modi betrieben wärde, um den `cloudflared`-Agenten zu verwalten, also die Softwarekomponente, die tatsächlich die dauerhafte Verbindung zwischen dim Server u dem Cloudflare-Netzwerk herstellt. Das Verständnis dieser beiden Modi isch entscheidend für die Wahl des richtigen Setups für dini Umgebung.

## Interner Modus (Standard)

Im internen Modus übernimmt DockFlare die volle Verantwortung für die Verwaltung des `cloudflared`-Agenten.

### Wie es funktioniert
Wenn DockFlare startet, wird es automatisch:
1.  Einen eigenen Docker-Container erstellen, auf dem das `cloudflare/cloudflared`-Image läuft.
2.  Diesen Agenten-Container konfigurieren, um sich mit dim Cloudflare-Konto zu verbinden u den in dini DockFlare-Istellige angegebenen Tunnel zu bruuche.
3.  Sicherstellen, dass der Agent läuft, u ihn im Fehlerfall neu starten.
4.  Automatisch alle relevanten Istellige anwenden, wie z.B. die Aktivierung des Prometheus-Metrik-Endpunkts.

Das isch der **Standard- u empfohlene** Modus für die meisten Benutzer.

### Vorteile
*   **Einfachheit:** Es isch eine "Zero-Configuration"-Einrichtung. DockFlare übernimmt alles für di.
*   **Garantierte Kompatibilität:** DockFlare stellt sicher, dass der Agent so konfiguriert isch, wie er damit arbeiten cha.
*   **Zentrale Verwaltung:** Alles, was mit dini Tunneln zu tun hat, wird von DockFlare verwaltet.

### Nachteile
*   **Weniger Kontrolle:** du hesch nur eingeschränkte Kontrolle über die Konfiguration des `cloudflared`-Agenten, abseits dessen, was DockFlare offenlegt.

---

## Externer `cloudflared` Modus

Im externen Modus si du selbst für den Betrieb u die Verwaltung des `cloudflared`-Agenten verantwortlich. DockFlare verbindet sich mit diesem bestehenden Agenten, anstatt einen eigenen zu erstellen.

### Wie es funktioniert
DockFlare wird **kei** `cloudflared`-Container erstellen. Stattdessen geht es davon aus, dass irgendwo ein `cloudflared`-Agent läuft, den es bruuche cha. Das könnte sein:
*   Ein `cloudflared`-Prozess, der direkt auf dem Host-Betriebssystem läuft (z.B. als `systemd`-Dienst).
*   En `cloudflared`-Container, wo du säuber mit ere separierte `docker-compose.yml`-Datei oder mit eme Docker-Run-Befehl verwaltisch.
*   Ein `cloudflared`-Agent, der auf einer komplett anderen Maschine läuft.

Das isch ein **fortgeschrittener Modus**, der für Benutzer mit spezifischen Anforderungen oder komplexen bestehenden Setups gedacht isch.

### Vorteile
*   **Maximale Kontrolle:** du hesch die volle Kontrolle über den `cloudflared`-Agenten, einschliesslich seiner Version, Kommandozeilenargumente u seines Lebenszyklus.
*   **Integration in bestehende Setups:** Perfekt, wenn bereits ein `cloudflared`-Agent für andere Zwecke bei dir läuft.
*   **Entkopplung:** Entkoppelt den Lebenszyklus von DockFlare vom Lebenszyklus des `cloudflared`-Agenten.

### Nachteile
*   **Komplexität:** du bisch dafür verantwortlich, sicherzustellen, dass der `cloudflared`-Agent läuft, richtig konfiguriert u mit dem richtigen Tunnel verbunden isch.
*   **Konfigurationsaufwand:** du muesch DockFlare konfigurieren, um diesen externen Agenten zu nutzen.

### So aktivier den externen Modus
Um den externen Modus zu aktivieren, muesch die folgenden Umgebungsvariablen für den DockFlare-Container setzen:

*   `USE_EXTERNAL_CLOUDFLARED=true`: Aktiviert den externen Modus.
*   `EXTERNAL_TUNNEL_ID`: Muss auf die UUID des Tunnels gesetzt wärde, auf die din externer `cloudflared`-Agent konfiguriert isch.

Wenn diese Variablen gesetzt si, überspringt DockFlare die interne Agentenverwaltung u sendet stattdessen alle Ingress-Regelkonfigurationen an den Tunnel, der durch `EXTERNAL_TUNNEL_ID` angegeben isch.
