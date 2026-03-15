# Backup u Wiederherstellung

DockFlare 3.0 führt ein vollständiges Backup-Archiv ein. Damit chasch einen Master auf neue Hardware umziehen, sich nach einem Ausfall erholen oder Upgrades vorbereiten, ohne das rohe Datenverzeichnis direkt anfassen zu müesse.

## Was gesichert wird
- `dockflare.key` – Der Fernet-Schlüssel, mit dem sich jede verschlüsselte Datei entschlüsseln lässt.
- `dockflare_config.dat` – Verschlüsselte Cloudflare-Anmeldedaten, UI-Konten u Laufzeiteinstellungen.
- `agent_keys.dat` – Verschlüsselte Agent-API-Schlüssel u Audit-Metadaten.
- `state.json` – Ein unverschlüsselter JSON-Spiegel dinere Regeln, Agenten u Access Groups.
- `manifest.json` – Prüfsummen u Versionsinformationen für das Archiv (wird automatisch erzeugt).

Alle diese Dateien wärde in einer einzelnen `dockflare_backup_YYYYMMDD_HHMMSS.zip` gebündelt. Bhalt das ZIP-Archiv u die extrahierten Dateien zusammen auf. Ohne `dockflare.key` si die verschlüsselten Artefakte nid nutzbar.

## Ein Backup erstellen
1. Mach uf in der Master-UI **Settings → Backup & Restore**.
2. Klick auf **Download Backup (.zip)**.
3. Bhalt das Archiv an einem sicheren Ort auf. Behandle es wie sensible Zugangsdaten, denn es enthält alles, was für die Steuerung din Cloudflare-Kontos über DockFlare nötig isch.

Backups chöi erstellt wärde, während der Master läuft. Jedes Archiv enthält ein Manifest mit SHA-256-Hashes, sodass sich beschädigte Downloads leicht erkennen lassen.

## Wiederherstellung auf einem existierenden Master
1. Gang zu **Settings → Backup & Restore**.
2. Lad die `.zip`-Datei über **Restore from Backup** hoch.
3. Bestätig die Warnung: Eine Wiederherstellung überschreibt die vorhandene Konfiguration, Agent-Schlüssel u Regeln.

DockFlare schreibt die verschlüsselten Dateien zrugg, lädt `state.json` neu u setzt falls nötig es Neustart-Flag. Dr Container beendet sich churz druf sälber, demit Docker ne mit dr neue Konfiguration neu startet. Nachhär isch d'Web UI wieder mit de wiederhergstelltete Aamäldedate verfügbar.

Ältere `state.json`-Dateien aus früheren Versionen wärde für Teilwiederherstellungen weiterhin akzeptiert. Das Hochladen einer reinen JSON-Datei ersetzt nur Regeln u lässt die verschlüsselte Konfiguration unverändert.

## Wiederherstellung während des Einrichtungsassistenten
Bei Neuinstallationen erscheint jetzt vor Schritt 1 des Einrichtungsassistenten der Link **Restore from Backup**.

1. Lad die Backup-ZIP-Datei hoch.
2. DockFlare schreibt die verschlüsselten Artefakte u den Zustand auf die Festplatte.
3. Der Container startet automatisch neu. Mäld di aa nach dem Neustart mit dem wiederhergestellten Administratorkonto an.

Dieser Ablauf isch der schnellste Weg, um einen produktiven Master zu klonen oder sich nach dem Löschen des Datenvolumens zu erholen. Du muesch den Assistenten nid erneut durchlaufen u auch die Cloudflare-Anmeldedaten nid noch einmal eingeben.

## Nach der Wiederherstellung
- Mach uf **Settings → Backup & Restore**, um den neuesten Zeitstempel im Manifest zu prüfen.
- Prüef unter **Agents → Overview**, öb sich registrierte Agenten wieder verbinden. Stell bi Bedarf neui Agent-Schlüssel uus, falls du die zwüscheziit rotiert hesch.
- Stoss e Abglich aa, wänn du i e angri Umgebig wiederhergstellt hesch (`Actions → Reconcile Now`).

Führ regelmässig Offline-Backups durch u kombinier diese idealerweise mit Versionskontrolle für dini Compose-Stack, damit du die gesamte Bereitstellige im Bedarfsfall schnell neu aufbauen chöi.
