# Backup & Restore

DockFlare 3.0 introduces a full backup archive so you can move a master to fresh hardware, recover from failure, or stage upgrades without touching the raw data directory.

## What Gets Saved
- `dockflare.key` – the Fernet key that unlocks every encrypted file.
- `dockflare_config.dat` – encrypted Cloudflare credentials, UI accounts, and runtime settings.
- `agent_keys.dat` – encrypted agent API keys and audit metadata.
- `state.json` – plain JSON mirror of rules, agents, and access groups.
- `manifest.json` – checksums and version info for the archive (auto generated).

All of these files are bundled into a single `dockflare_backup_YYYYMMDD_HHMMSS.zip`. Keep the ZIP and the extracted files together; without `dockflare.key` the encrypted artefacts are useless.

## Creating a Backup
1. Open **Settings → Backup & Restore** in the master UI.
2. Click **Download Backup (.zip)**.
3. Store the archive somewhere safe. Treat it like credentials—it contains everything needed to control your Cloudflare account through DockFlare.

Backups can be taken while the master is running. Each archive includes a manifest with SHA-256 hashes so corrupted downloads are easy to spot.

## Restoring on an Existing Master
1. Go to **Settings → Backup & Restore**.
2. Upload the `.zip` through **Restore from Backup**.
3. Confirm the warning: restoring overwrites configuration, agent keys, and rules.

DockFlare rehydrates the encrypted files, reloads `state.json`, and, if needed, writes a restart flag. The container exits a few seconds later so Docker can start it back up with the new configuration. The UI reopens with the restored credentials.

Legacy `state.json` files are still accepted for partial restores. Uploading a bare JSON file only replaces rules and skips the encrypted config.

## Restoring During the Setup Wizard
Fresh installs now have a **Restore from Backup** link before Step 1 of the Pre-Flight wizard.

1. Upload the backup ZIP.
2. DockFlare writes the encrypted artefacts and state to disk.
3. The container restarts automatically; when it comes back, sign in with the restored admin account.

This flow is the fastest way to clone a production master or recover after wiping the data volume. You do not need to re-run the wizard or re-enter Cloudflare credentials.

## After the Restore
- Visit **Settings → Backup & Restore** to confirm the latest manifest timestamp.
- Check **Agents → Overview** to ensure enrolled agents reconnect. Reissue agent keys if you rotated them.
- Trigger a reconciliation if you restored into a different environment (`Actions → Reconcile Now`).

Keep regular offline backups and pair them with version control for your compose stack so you can rebuild the entire deployment quickly.
