# Using the Web UI

The DockFlare Web UI is a powerful tool for managing, monitoring, and configuring your services. It provides a user-friendly interface for tasks that go beyond simple Docker label configuration.

## The Dashboard (Main Page)

The first page you see after logging in is the main dashboard. This is your central hub for viewing the state of all your managed services.

*   **Managed Ingress Rules Table:** This table lists every ingress rule that DockFlare is managing, whether it comes from a Docker container or was created manually.
    *   **Hostname:** The public hostname of the service.
    *   **Service:** The internal destination URL.
    *   **Source:** Indicates if the rule is from `Docker` or was created `Manually` in the UI.
    *   **Status:** Shows if the rule is `active`, `pending_deletion`, or has a `UI Override`.
    *   **Access:** Displays the Access Policy applied to the rule (e.g., `Public`, `Authenticate`, or the name of an Access Group).
    *   **Manage Rule:** This button allows you to edit any rule.
*   **Real-time Logs:** Below the table, you'll find a real-time log viewer that streams logs from the DockFlare backend, which is invaluable for debugging.

## Managing Rules

The UI gives you full control over your ingress rules.

*   **Add Manual Rule:** The "Add Manual Rule" button lets you create ingress rules for services that are not running in Docker (e.g., a service on another machine in your LAN). The form allows you to specify the hostname, service URL, and optionally apply an Access Group.
*   **Edit any Rule:** The "Manage Rule" button next to every rule opens a modal where you can change its configuration. This is how you can apply a UI override to a rule that was originally created from Docker labels.
*   **Revert to Labels:** If a rule from Docker has a UI override, a "Revert to Labels" button will appear, allowing you to discard your manual changes and let the rule be controlled by its Docker labels again.

## Access Policies Page

This page is the central location for managing your reusable **Access Groups**. From here, you can:
*   **Create** new Access Groups with complex rules (e.g., based on email, IP, or country).
*   **Edit** existing Access Groups.
*   **Delete** Access Groups that are no longer in use.

For more details, see the [Access Policy Best Practices & Examples](Access-Policy-Best-Practices.md) guide.

## Settings Page

The Settings page contains various administrative and configuration options:

*   **Cloudflare Tunnels:** This section lists all the Cloudflare Tunnels found on your account, their status, and their connected `cloudflared` agents. You can also view all CNAME DNS records pointing to any of your tunnels.
*   **Backup & Restore:** Download a full DockFlare backup archive (`.zip`) containing encrypted config, agent keys, and state, or upload a previously exported archive to restore the instance.
*   **Security:**
    *   **Change Password:** Change your password for the Web UI.
    *   **Disable Password Login:** For advanced use cases where you place DockFlare behind another authentication proxy.
*   **Cloudflare Credentials:** Allows you to update your Cloudflare Account ID and API Token after the initial setup.
*   **Core Configuration:** Lets you change settings like the Tunnel Name and Rule Grace Period.
