# Persistenter Status

DockFlare ist eine zustandsbehaftete Anwendung. Sie muss die verwalteten Dienste, UI-Overrides und weitere Konfigurationsdetails nachverfolgen. Dieser Zustand wird auf der Festplatte gespeichert, damit Ihre Konfiguration beim Neustart oder bei einer Neuerstellung des DockFlare-Containers nicht verloren geht.

## Wie der Status gespeichert wird

DockFlare speichert seinen Zustand in drei wichtigen Dateien im Verzeichnis `/app/data` innerhalb des Containers:

1.  `dockflare_config.dat`: Dies ist die wichtigste Datei. Sie enthält alle zentralen Einstellungen und sensiblen Informationen in **verschlüsselter** Form. Dazu gehören:
    *   Ihr Cloudflare-API-Token und Ihre Account-ID
    *   Der Passwort-Hash für die DockFlare-UI
    *   Zentrale Einstellungen aus der UI, etwa Tunnelname und Zonen-IDs

2.  `agent_keys.dat`: Ein verschlüsselter Speicher mit allen Agent-API-Schlüsseln und den dazugehörigen Metadaten (Besitzer, Status, Zeitstempel). Wenn diese Datei sicher aufbewahrt wird, können veraltete Schlüssel nicht erneut verwendet werden.

3.  `state.json`: Diese Datei speichert den dynamischen Status Ihrer verwalteten Dienste im JSON-Klartextformat. Dazu gehören:
    *   Alle von DockFlare verwalteten Ingress-Regeln, unabhängig davon, ob sie aus Docker-Labels stammen oder manuell in der UI erstellt wurden
    *   Alle UI-Overrides für Access Policies
    *   Sämtliche von Ihnen angelegten Access Groups
    *   Der Status `pending deletion` für Dienste, die gestoppt wurden, sich aber noch innerhalb ihrer Grace Period befinden

## Die Bedeutung eines persistenten Volumes

Da Ihre gesamte Konfiguration im Verzeichnis `/app/data` gespeichert wird, ist es **absolut entscheidend**, dass Sie dieses Verzeichnis auf ein persistentes Volume auf Ihrem Host-Rechner mappen.

Wenn Sie kein persistentes Volume verwenden, **gehen all Ihre Einstellungen, UI-Passwörter und Regelkonfigurationen jedes Mal verloren**, wenn der DockFlare-Container entfernt und neu erstellt wird (z.B. beim Aktualisieren des Images).

### Empfohlene Docker-Compose-Konfiguration

Die empfohlene `docker-compose.yml`-Konfiguration erledigt dies für Sie automatisch, indem sie ein benanntes Volume definiert und es nach `/app/data` mountet:

```yaml
services:
  dockflare:
    # ... other settings
    volumes:
      # This line ensures your data is persisted
      - ./dockflare_data:/app/data

volumes:
  # This defines the named volume on your host
  dockflare_data:
```

Mit dieser Konfiguration werden Ihre Dateien `dockflare_config.dat`, `agent_keys.dat` und `state.json` in einem Verzeichnis namens `dockflare_data` auf Ihrem Host gespeichert, sodass Ihr Setup über Container-Updates hinweg sicher erhalten bleibt.

## Backup und Wiederherstellung

DockFlare bündelt nun alle kritischen Daten in ein einzelnes verschlüsseltes Backup-Archiv. Redis-Caches werden dabei ausgelassen, da sie sicher im privaten Netzwerk `dockflare-internal` neu aufgebaut werden können. Das Panel **Einstellungen → Backup & Wiederherstellung** ermöglicht Ihnen den Download einer `.zip`-Datei, die enthält:

* `dockflare_config.dat`
* `dockflare.key`
* `agent_keys.dat`
* `state.json` (falls vorhanden)
* Ein Manifest mit Prüfsummen zur Integritätsverifizierung

Beim Wiederherstellen des Archivs werden diese Dateien neu erstellt und in die laufende Instanz geladen. Ältere Uploads einer reinen `state.json` werden weiterhin akzeptiert, stellen aber nur Regel-Metadaten wieder her. Zugangsdaten müssen danach manuell neu eingegeben werden.
Nach einer vollständigen Archiv-Wiederherstellung startet DockFlare den Container automatisch neu, damit die verschlüsselte Konfiguration sofort geladen wird.
