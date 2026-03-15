# Persistenter Status

DockFlare isch eine zustandsbehaftete Anwendung. Du muesch die verwalteten Dienste, UI-Overrides u weitere Konfigurationsdetails nachverfolgen. Dieser Zustand wird auf der Festplatte gespeichert, damit dini Konfiguration beim Neustart oder bei einer Neuerstellung des DockFlare-Containers nid verloren geht.

## Wie der Status gespeichert wird

DockFlare speichert seinen Zustand in drei wichtigen Dateien im Verzeichnis `/app/data` innerhalb des Containers:

1.  `dockflare_config.dat`: Das isch die wichtigste Datei. Si enthält alle zentralen Istellige u sensiblen Informationen in **verschlüsselter** Form. Dazu gehören:
    *   din Cloudflare-API-Token u dini Account-ID
    *   Der Passwort-Hash für die DockFlare-UI
    *   Zentrale Istellige aus der UI, etwa Tunnelname u Zonen-IDs

2.  `agent_keys.dat`: Ein verschlüsselter Speicher mit allen Agent-API-Schlüsseln u den dazugehörigen Metadaten (Besitzer, Status, Zeitstempel). Wenn diese Datei sicher aufbewahrt wird, chöi veraltete Schlüssel nid erneut verwendet wärde.

3.  `state.json`: Diese Datei speichert den dynamischen Status dinere verwalteten Dienste im JSON-Klartextformat. Dazu gehören:
    *   Alle von DockFlare verwalteten Ingress-Regeln, unabhängig davon, öb sie aus Docker-Labels stammen oder manuell in der UI erstellt wurden
    *   Alle UI-Overrides für Access Policies
    *   Sämtliche von dir angelegten Access Groups
    *   Der Status `pending deletion` für Dienste, die gestoppt wurden, sich aber noch innerhalb ihrer Grace Period befinden

## Die Bedeutung eines persistenten Volumes

Da dini gesamte Konfiguration im Verzeichnis `/app/data` gespeichert wird, isch es **absolut entscheidend**, dass du dieses Verzeichnis auf ein persistentes Volume auf dim Host-Rechner mappen.

Wänn du kei persistents Volume bruuchsch, **geit dr jedes Mal alles verlore (Istellige, UI-Passwörter u Regelkonfiguratione)**, sobald dr DockFlare-Container entfernt u neu erstellt wird (z.B. biim Aktualisiere vom Image).

### Empfohlene Docker-Compose-Konfiguration

Die empfohlene `docker-compose.yml`-Konfiguration erledigt dies für di automatisch, indem sie ein benanntes Volume definiert u es nach `/app/data` mountet:

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

Mit dieser Konfiguration wärde dini Dateien `dockflare_config.dat`, `agent_keys.dat` u `state.json` in einem Verzeichnis namens `dockflare_data` auf dim Host gespeichert, sodass din Setup über Container-Updates hinweg sicher erhalten bleibt.

## Backup u Wiederherstellung

DockFlare bündelt nun alle kritischen Daten in ein einzelnes verschlüsseltes Backup-Archiv. Redis-Caches wärde dabei ausgelassen, da sie sicher im privaten Netzwerk `dockflare-internal` neu aufgebaut wärde chöi. Das Panel **Istellige → Backup & Wiederherstellung** ermöglicht dir den Download einer `.zip`-Datei, die enthält:

* `dockflare_config.dat`
* `dockflare.key`
* `agent_keys.dat`
* `state.json` (falls vorhanden)
* Ein Manifest mit Prüfsummen zur Integritätsverifizierung

Beim Wiederherstellen des Archivs wärde diese Dateien neu erstellt u in die laufende Instanz geladen. Ältere Uploads einer reinen `state.json` wärde weiterhin akzeptiert, stellen aber nur Regel-Metadaten wieder her. Zugangsdaten müesse danach manuell neu eingegeben wärde.
Nach einer vollständigen Archiv-Wiederherstellung startet DockFlare den Container automatisch neu, damit die verschlüsselte Konfiguration sofort geladen wird.
