# Backup und Wiederherstellung

DockFlare 3.0 führt ein vollständiges Backup-Archiv ein. Damit können Sie einen Master auf neue Hardware umziehen, sich nach einem Ausfall erholen oder Upgrades vorbereiten, ohne das rohe Datenverzeichnis direkt anfassen zu müssen.

## Was gesichert wird
- `dockflare.key` – Der Fernet-Schlüssel, mit dem sich jede verschlüsselte Datei entschlüsseln lässt.
- `dockflare_config.dat` – Verschlüsselte Cloudflare-Anmeldedaten, UI-Konten und Laufzeiteinstellungen.
- `agent_keys.dat` – Verschlüsselte Agent-API-Schlüssel und Audit-Metadaten.
- `state.json` – Ein unverschlüsselter JSON-Spiegel Ihrer Regeln, Agenten und Access Groups.
- `manifest.json` – Prüfsummen und Versionsinformationen für das Archiv (wird automatisch erzeugt).

Alle diese Dateien werden in einer einzelnen `dockflare_backup_YYYYMMDD_HHMMSS.zip` gebündelt. Bewahren Sie das ZIP-Archiv und die extrahierten Dateien zusammen auf. Ohne `dockflare.key` sind die verschlüsselten Artefakte nicht nutzbar.

## Ein Backup erstellen
1. Öffnen Sie in der Master-UI **Settings → Backup & Restore**.
2. Klicken Sie auf **Download Backup (.zip)**.
3. Bewahren Sie das Archiv an einem sicheren Ort auf. Behandeln Sie es wie sensible Zugangsdaten, denn es enthält alles, was für die Steuerung Ihres Cloudflare-Kontos über DockFlare nötig ist.

Backups können erstellt werden, während der Master läuft. Jedes Archiv enthält ein Manifest mit SHA-256-Hashes, sodass sich beschädigte Downloads leicht erkennen lassen.

## Wiederherstellung auf einem existierenden Master
1. Gehen Sie zu **Settings → Backup & Restore**.
2. Laden Sie die `.zip`-Datei über **Restore from Backup** hoch.
3. Bestätigen Sie die Warnung: Eine Wiederherstellung überschreibt die vorhandene Konfiguration, Agent-Schlüssel und Regeln.

DockFlare schreibt die verschlüsselten Dateien zurück, lädt `state.json` neu und setzt bei Bedarf ein Neustart-Flag. Der Container beendet sich wenige Sekunden später selbst, damit Docker ihn mit der neuen Konfiguration neu starten kann. Danach ist die Benutzeroberfläche wieder mit den wiederhergestellten Anmeldedaten verfügbar.

Ältere `state.json`-Dateien aus früheren Versionen werden für Teilwiederherstellungen weiterhin akzeptiert. Das Hochladen einer reinen JSON-Datei ersetzt nur Regeln und lässt die verschlüsselte Konfiguration unverändert.

## Wiederherstellung während des Einrichtungsassistenten
Bei Neuinstallationen erscheint jetzt vor Schritt 1 des Einrichtungsassistenten der Link **Restore from Backup**.

1. Laden Sie die Backup-ZIP-Datei hoch.
2. DockFlare schreibt die verschlüsselten Artefakte und den Zustand auf die Festplatte.
3. Der Container startet automatisch neu. Melden Sie sich nach dem Neustart mit dem wiederhergestellten Administratorkonto an.

Dieser Ablauf ist der schnellste Weg, um einen produktiven Master zu klonen oder sich nach dem Löschen des Datenvolumens zu erholen. Sie müssen den Assistenten nicht erneut durchlaufen und auch die Cloudflare-Anmeldedaten nicht noch einmal eingeben.

## Nach der Wiederherstellung
- Öffnen Sie **Settings → Backup & Restore**, um den neuesten Zeitstempel im Manifest zu prüfen.
- Prüfen Sie unter **Agents → Overview**, ob sich registrierte Agenten wieder verbinden. Stellen Sie bei Bedarf neue Agent-Schlüssel aus, falls Sie diese zwischenzeitlich rotiert haben.
- Stoßen Sie einen Abgleich an, wenn Sie in eine andere Umgebung wiederhergestellt haben (`Actions → Reconcile Now`).

Führen Sie regelmäßig Offline-Backups durch und kombinieren Sie diese idealerweise mit Versionskontrolle für Ihren Compose-Stack, damit Sie die gesamte Bereitstellung im Bedarfsfall schnell neu aufbauen können.
