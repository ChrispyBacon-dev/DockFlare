# Zwischen den Modi wechseln

Du chasch DockFlare jederzeit zwischen dem **Internen** (Standard) u dem **Externen** `cloudflared`-Modus umschalten. Dieser Leitfaden erklärt den Ablauf für einen reibungslosen Übergang.

Einen detaillierten Vergleich der beiden Modi findsch auf der Seite [Interner vs. Externer `cloudflared`](Internal-vs-External-cloudflared.md).

---

## Wechsel vom Internen zum Externen Modus

Dieser Prozess beinhaltet die Einrichtung din eigenen `cloudflared`-Agenten u die anschliessende Konfiguration von DockFlare, diesen zu nutzen.

**Schritt 1: Richt dini externen `cloudflared`-Agenten ii**

Zuerst muesch dini eigenen `cloudflared`-Agenten einrichten u ausführen. Das cha ein Prozess auf dem Host-Betriebssystem oder in einem separaten Docker-Container sein.

*   lueg dass er so konfiguriert isch, dass er en bestimmte Cloudflare Tunnel nutzt.
*   Schrib dr d'**Tunnel ID** (UUID) uuf.
*   Start de Agent u lueg, dass er korrekt lauft u im Cloudflare-Dashboard als "connected" (verbunde) angezeigt wird.

**Schritt 2: DockFlare rekonfigurieren u neu starten**

Als Nächstes muesch die Umgebungsvariablen für dini DockFlare-Container aktualisieren, um in den externen Modus zu wechseln.

In dinere `docker-compose.yml`:
```yaml
services:
  dockflare:
    image: alplat/dockflare:stable
    # ... other settings
    environment:
      # Enable external mode
      - USE_EXTERNAL_CLOUDFLARED=true
      # Provide the ID of your running tunnel
      - EXTERNAL_TUNNEL_ID=your-tunnel-uuid-goes-here
```

**Schritt 3: Die Änderung anwenden**

Führ `docker compose up -d` aus, um den DockFlare-Container mit den neuen Umgebungsvariablen neu zu erstellen.

Wenn der aktualisierte DockFlare-Container startet:
1.  Wird er erkennen, dass `USE_EXTERNAL_CLOUDFLARED` auf `true` gesetzt isch.
2.  Wird er seinen eigenen verwalteten `cloudflared-agent`-Container **stoppen u entfernen**.
3.  Wird er beginnen, alle seine Ingress-Regelkonfigurationen an den durch `EXTERNAL_TUNNEL_ID` angegebenen Tunnel zu senden.

dini Dienste wärde nun von dim extern verwalteten `cloudflared`-Agenten bereitgestellt.

---

## Wechsel vom Externen zum Internen Modus

Dieser Prozess isch einfacher, da du dabei DockFlare wieder die Kontrolle überlassen.

**Schritt 1: DockFlare neu konfigurieren**

Entfern die Umgebungsvariablen für den externen Modus aus dinere DockFlare `docker-compose.yml`-Datei.

```yaml
services:
  dockflare:
    image: alplat/dockflare:stable
    # ... other settings
    environment:
      # Remove the following two lines
      # - USE_EXTERNAL_CLOUDFLARED=true
      # - EXTERNAL_TUNNEL_ID=your-tunnel-uuid-goes-here
```

**Schritt 2: Die Änderung anwenden**

Führ `docker compose up -d` aus, um den DockFlare-Container neu zu erstellen.

Wenn der aktualisierte DockFlare-Container startet:
1.  Wird er erkennen, dass `USE_EXTERNAL_CLOUDFLARED` auf `false` gesetzt isch.
2.  Wird er automatisch seinen eigenen internen `cloudflared-agent`-Container **erstellen, konfigurieren u starten**.
3.  Wird er diesen neuen Agenten so konfigurieren, dass er den in dini DockFlare-Istellige definierten Tunnelnamen verwendet.

**Schritt 3: dini externen Agenten ausser Betrieb nehmen**

Sobald du bestätigt hesch, dass dr neue intern Agent fehlerfrei lauft u dr Datenverkehr verarbeitet, chasch dini eigene `cloudflared`-Agenten sicher stoppe u entferne.
