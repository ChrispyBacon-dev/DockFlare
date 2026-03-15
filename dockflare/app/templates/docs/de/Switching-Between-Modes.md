# Zwischen den Modi wechseln

Sie können DockFlare jederzeit zwischen dem **Internen** (Standard) und dem **Externen** `cloudflared`-Modus umschalten. Dieser Leitfaden erklärt den Ablauf für einen reibungslosen Übergang.

Einen detaillierten Vergleich der beiden Modi finden Sie auf der Seite [Interner vs. Externer `cloudflared`](Internal-vs-External-cloudflared.md).

---

## Wechsel vom Internen zum Externen Modus

Dieser Prozess beinhaltet die Einrichtung Ihres eigenen `cloudflared`-Agenten und die anschließende Konfiguration von DockFlare, diesen zu nutzen.

**Schritt 1: Richten Sie Ihren externen `cloudflared`-Agenten ein**

Zuerst müssen Sie Ihren eigenen `cloudflared`-Agenten einrichten und ausführen. Dies kann ein Prozess auf dem Host-Betriebssystem oder in einem separaten Docker-Container sein.

*   Stellen Sie sicher, dass er so konfiguriert ist, dass er einen bestimmten Cloudflare Tunnel nutzt.
*   Notieren Sie sich die **Tunnel ID** (UUID).
*   Starten Sie den Agenten und bestätigen Sie, dass er korrekt ausgeführt wird und in Ihrem Cloudflare-Dashboard als "connected" (verbunden) angezeigt wird.

**Schritt 2: DockFlare rekonfigurieren und neu starten**

Als Nächstes müssen Sie die Umgebungsvariablen für Ihren DockFlare-Container aktualisieren, um in den externen Modus zu wechseln.

In Ihrer `docker-compose.yml`:
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

Führen Sie `docker compose up -d` aus, um den DockFlare-Container mit den neuen Umgebungsvariablen neu zu erstellen.

Wenn der aktualisierte DockFlare-Container startet:
1.  Wird er erkennen, dass `USE_EXTERNAL_CLOUDFLARED` auf `true` gesetzt ist.
2.  Wird er seinen eigenen verwalteten `cloudflared-agent`-Container **stoppen und entfernen**.
3.  Wird er beginnen, alle seine Ingress-Regelkonfigurationen an den durch `EXTERNAL_TUNNEL_ID` angegebenen Tunnel zu senden.

Ihre Dienste werden nun von Ihrem extern verwalteten `cloudflared`-Agenten bereitgestellt.

---

## Wechsel vom Externen zum Internen Modus

Dieser Prozess ist einfacher, da Sie dabei DockFlare wieder die Kontrolle überlassen.

**Schritt 1: DockFlare neu konfigurieren**

Entfernen Sie die Umgebungsvariablen für den externen Modus aus Ihrer DockFlare `docker-compose.yml`-Datei.

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

Führen Sie `docker compose up -d` aus, um den DockFlare-Container neu zu erstellen.

Wenn der aktualisierte DockFlare-Container startet:
1.  Wird er erkennen, dass `USE_EXTERNAL_CLOUDFLARED` auf `false` gesetzt ist.
2.  Wird er automatisch seinen eigenen internen `cloudflared-agent`-Container **erstellen, konfigurieren und starten**.
3.  Wird er diesen neuen Agenten so konfigurieren, dass er den in Ihren DockFlare-Einstellungen definierten Tunnelnamen verwendet.

**Schritt 3: Ihren externen Agenten außer Betrieb nehmen**

Sobald Sie bestätigt haben, dass der neue interne Agent fehlerfrei läuft und den Datenverkehr verarbeitet, können Sie Ihren eigenen `cloudflared`-Agenten sicher stoppen und entfernen.
