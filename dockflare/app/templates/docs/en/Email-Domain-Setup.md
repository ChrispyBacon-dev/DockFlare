# Domain Setup & Configuration

Once your Docker containers are running with the `email` profile, you can begin the automated setup process in the DockFlare Web UI.

## The Email Setup Wizard

1.  Navigate to the **Email** page in the left-hand sidebar.
2.  Click **Set Up Email Domain**.
3.  Select the **Cloudflare Zone** (domain) you wish to configure.
4.  Click **Confirm Setup**.

### What happens during setup?
DockFlare performs several automated steps via the Cloudflare API:
*   **Enables Email Routing** on your zone.
*   **Configures DNS:** Creates MX records, SPF (TXT), DMARC (TXT), and DKIM (CNAME) records as required by Cloudflare Email Routing.
*   **Provisions Storage:** Creates a dedicated R2 bucket for temporary transit buffering.
*   **Deploys Workers:** Deploys an Inbound Worker (to receive mail) and an Outbound Worker (to send mail).
*   **Initializes KV:** Creates a Cloudflare KV namespace to track mailbox quotas at the edge.

## Verifying DNS Health

DNS changes can take time to propagate. On the Email page, you will see a **DNS Records** card.
*   Click **Verify DNS** to check the current status of your MX, SPF, and DMARC records. (DKIM is managed automatically by Cloudflare Email Routing and is not separately verified here.)
*   The system will show green badges when the records are correctly detected in the public DNS.

## Updating / Redeploying Workers

If you update your DockFlare version or change your API permissions, you may need to refresh your workers.
*   Click the **Redeploy Workers** button.
*   This will re-upload the latest worker logic and re-sync all bindings (R2, KV, Webhook Secrets) without affecting your stored email data.

## Tearing Down a Domain

If you wish to stop hosting email for a domain:
*   Click **Teardown Domain**.
*   This will remove routing rules, Inbound/Outbound Workers, the R2 transit bucket, and DNS records from Cloudflare.
*   **Note:** This does *not* delete your local email data in the `mail_data` volume. Enable **Include local data** in the teardown dialog if you also want to wipe messages and attachments stored on your server.
