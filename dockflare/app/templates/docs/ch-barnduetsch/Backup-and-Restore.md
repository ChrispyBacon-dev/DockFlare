# Backup u Wiederhärstellig

DockFlare 3.0 het es vollständigs Backup-Archiv. Damit chasch e Master uf nöii Hardware umzügle, nach eme Usfall schnäll wieder härstelle oder es Upgrade vorbereite, ohni ds Dateiverzeichnis diräkt manuell aafasse z müesse.

## Was wird gsicheret?

* `dockflare.key` – dr Fernet-Schlüssu, mit em sich aui verschlüsslete Dateie entschlüssle löh
* `dockflare_config.dat` – verschlüssleti Cloudflare-Zuegangsdaten, UI-Konte u Laufzyt-Iistellige
* `agent_keys.dat` – verschlüssleti Agent-API-Schlüssle u Audit-Metadate
* `state.json` – e unverschlüsslete JSON-Spiegel vo dine Regle, Agente u Access Groups
* `manifest.json` – Prüefsummene u Versions-Infos fürs Archiv (wird automatisch erzeugt)

Aui die Dateie wärde i nere einzelne `dockflare_backup_YYYYMMDD_HHMMSS.zip` zämegfasst. Heb ds ZIP-Archiv u d extrahierte Dateie sicher uf. Ohni `dockflare.key` sy d verschlüsslete Artefakt nid bruuchbar.

## Es Backup erstelle

1. Gang i dr Master-UI uf **Settings → Backup & Restore**.
2. Klick uf **Download Backup (.zip)**.
3. Heb s Archiv a mene sichere Ort uf. Behandle's wie sensibli Zuegangsdaten, will es im Prinzip aues enthält, was du für d Steuerig vo dim Cloudflare-Konto über DockFlare bruchsch.

Backups chöi erstellt wärde, während dr Master louft. Jedes Archiv enthält es Manifest mit SHA-256-Hashes, damit beschädigti Downloads eifach erkannt wärde.

## Wiederhärstellig uf eme bestehende Master

1. Gang zu **Settings → Backup & Restore**.
2. Lad d `.zip`-Datei über **Restore from Backup** uf.
3. Bestätig d Warnig: E Wiederhärstellig überschrybt d vorhandeni Konfiguration, Agent-Schlüssle u Regle.

DockFlare schrybt die verschlüsslete Dateie zrügg, lädt `state.json` neu u setzt falls nötig es Neustart-Flag. Dr Container beendet sech churz druf sälber, demit Docker ne mit dr neue Konfiguration neu startet. Nachhär isch d Web UI wieder mit de wiederhärgstelltete Aamäldedate verfügbar.

Älteri `state.json`-Dateie us früehnere Versione wärde für Teil-Wiederhärstellig wyterhi akzeptiert. Wänn du nume e JSON-Datei ufladsch, wärde nume Regle ersetzt; d verschlüssleti Konfiguration blybt unveränderet.

## Wiederhärstellig während em Iirichtigsassistent

Bi Neuinstallatione erschynt vor Schritt 1 vom Iirichtigsassistent dr Link **Restore from Backup**.

1. Lad ds Backup-ZIP uf.
2. DockFlare schrybt d verschlüsslete Artefakt u dr Status uf d Feschtplatte.
3. Dr Container startet automatisch neu. Mäld di nach em Neustart mit em wiederhärgstelltete Administratorkonto aa.

Das isch dr schnäuschti Wäg, zum e produktive Master z klone oder sech nach em Lösche vom Datenvolume z erhole. Du muesch dr Assistent nid no einisch dürloufe u ou d Cloudflare-Zuegangsdaten nid no einisch neu iigäh.

## Nach dr Wiederhärstellig

* Gang uf **Settings → Backup & Restore**, zum dr nöischte Zytstempel im Manifest z prüefe.
* Prüef under **Agents → Overview**, ob registrierti Agente sech wieder verbinde.
* Stoss e Abglich aa, wänn du i e angri Umgebig wiederhärgstellt hesch (`Actions → Reconcile Now`).

Mach regelmässig Offline-Backups u kombinier si idealerwys mit Versionskontrolle für dini Compose-Stacks, damit du dini ganz Bereitstellig im Notfall schnäll wider ufbaue chasch.
