# Mailbox & Quota Management

The **Mailbox Management** card on the Email page is where you control who can receive mail and how much storage they are allowed to use.

## Creating Mailboxes

1.  Click **Add Mailbox**.
2.  **Address:** Enter the desired prefix (e.g., `info`). The domain is automatically appended.
3.  **Display Name:** The name shown to recipients (e.g., `Support Team`).
4.  **Quota:** Select the initial storage limit.

## Understanding the Quota System

DockFlare uses a tiered quota system to ensure your server doesn't run out of disk space while providing a graceful experience for users.

### Soft Limit (Quota)
When a mailbox exceeds its configured quota:
*   The system inserts a **Warning Email** from a system address into the user's Inbox.
*   The user can still receive mail until they hit the Hard Limit.
*   The quota bar in the Master UI will turn **Yellow**.

### Hard Limit (Rejection)
The Hard Limit is automatically calculated as **Soft Limit + 15% (minimum 10MB grace buffer)**.
*   **Edge Rejection:** Rejection happens at the Cloudflare Edge. The sender's mail server receives an SMTP error **5.2.2 Mailbox full**.
*   The email never enters your R2 transit bucket or your local server, saving bandwidth.
*   The quota bar in the Master UI will turn **Red**.

## Catch-all Mailboxes

A Catch-all mailbox receives all emails sent to your domain that do not match an existing, specific mailbox.
1.  Click **Configure Catch-all**.
2.  Select a destination mailbox.
3.  Click **Enable**.

## Auto-Responders (Vacation Mode)

You can set up automated replies for any mailbox:
1.  Click the **Auto-Responder** icon (robot) next to a mailbox.
2.  Enter your message and subject.
3.  Set a **Date Range** for when the responder should be active.
4.  **Reply Interval:** Set how often the responder should reply to the same sender (e.g., once every 24 hours) to prevent "email loops."
