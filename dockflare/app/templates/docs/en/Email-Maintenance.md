# Maintenance & Troubleshooting

DockFlare Email is designed to be low-maintenance, but understanding how to handle backups and common issues is important for long-term reliability.

## Backup & Restore

All your email data is stored in the `mail_data` Docker volume. To perform a backup:

1.  **Full Volume Backup:** Back up the entire volume folder on your host machine. This is the safest option as it captures the raw SQLite database and all attachment files.
2.  **UI Backup:** On the **Email** page, find the **Backup & Restore** card and click **Download Backup**. This generates a ZIP archive of your email data. Note: this backup contains emails and attachments in plain text — store it securely.

To restore:
1.  Ensure the `mail_data` volume is mounted in your `docker-compose.yml`.
2.  On the **Email** page in the **Backup & Restore** card, select your ZIP file and click **Restore Backup**. This will permanently overwrite existing email data.

## Logs

Debugging delivery issues often requires looking at the logs of the `dockflare-mail-manager` container.

```bash
docker logs -f dockflare-mail-manager
```

The Email page also includes a **Delivery Logs** card. Click **Investigate** to open the log viewer, which has two tabs:
*   **Outbound Log:** History of all outbound email attempts.
*   **Bounce Log:** History of all delivery failures (NDRs) for emails you sent.

## Resilience & Self-Healing

### R2 Buffering
If your server goes offline (e.g., power outage, internet downtime), the Cloudflare Inbound Worker will notice that your local webhook is unreachable. It will keep the email safely in the **R2 temp_cache**.
*   The worker runs a **Cron Job** every 5 minutes.
*   It will automatically retry delivery of any buffered emails until your server is back online.

### Filesystem Parity
The Mail Manager includes a startup routine that ensures the database and the filesystem are in sync. If an attachment file exists but has no database record (an "orphan"), it will be automatically purged to save space.

## Common Issues

### "Worker Error" in Logs
Ensure your API Token has the `Workers Scripts` and `Workers KV Storage` permissions. If you recently updated DockFlare, you may need to click **Redeploy Workers** on the Email page to sync new environment variables.

### Mail is delayed
Check the **Cron** logs in the Cloudflare Worker dashboard. If your local server is under heavy load or having network issues, the worker will buffer mail to R2 and deliver it once your server responds.
