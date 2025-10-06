# Using the Web UI

The DockFlare Web UI is a powerful tool for managing, monitoring, and configuring your services. It provides a user-friendly interface for tasks that go beyond simple Docker label configuration.

## The Dashboard (Main Page)

The first page you see after logging in is the main dashboard. This is your central hub for viewing the state of all your managed services.

*   **Managed Ingress Rules Table:** This table lists every ingress rule that DockFlare is managing, whether it comes from a Docker container or was created manually.
    *   **Hostname:** The public hostname of the service.
    *   **Service:** The internal destination URL.
    *   **Source:** Indicates if the rule is from `Docker` or was created `Manually` in the UI.
    *   **Status:** Shows if the rule is `active`, `pending_deletion`, or has a `UI Override`.
    *   **Access:** Displays the applied Access Group and mode badge. Expect to see `Public` or `Authenticated` labels, cascaded group names, and quick links to the Cloudflare dashboard when reusable policies sync.
    *   **Manage Rule:** This button allows you to edit any rule.
*   **Real-time Logs:** Below the table, you'll find a real-time log viewer that streams logs from the DockFlare backend, which is invaluable for debugging.

## Managing Rules

The UI gives you full control over your ingress rules.

*   **Add Manual Rule:** The "Add Manual Rule" button lets you create ingress rules for services that are not running in Docker (e.g., a service on another machine in your LAN). The form allows you to specify the hostname, service URL, and optionally apply an Access Group.
*   **Edit any Rule:** The "Manage Rule" button next to every rule opens a modal where you can change its configuration. This is how you can apply a UI override to a rule that was originally created from Docker labels.
*   **Revert to Labels:** If a rule from Docker has a UI override, a "Revert to Labels" button will appear, allowing you to discard your manual changes and let the rule be controlled by its Docker labels again.

## Access Policies Page

This page is the central location for managing your reusable **Access Groups** and securing your DNS zones with wildcard policies.

### Advanced Access Policies

From the Access Groups section, you can:
*   **Create** new Access Groups using the two-tab modal (Authenticated vs Public). Guidance banners update per tab so you understand when DockFlare will emit a Cloudflare `allow` or `bypass` decision.
*   **Edit** existing Access Groups. The modal enforces mode-specific validation (emails required for Authenticated) and keeps Geo/IP settings visible for both modes.
*   **Delete** Access Groups that are no longer in use (system policies like `public-default-bypass` cannot be deleted).
*   **Sync from Cloudflare** to import existing DockFlare reusable policies from your account.
*   Use the action menu beside each entry to open the matching policy directly in the Cloudflare dashboard via the Cloudflare icon shortcut.

**Note:** The `public-default-bypass` system policy is automatically created and managed by DockFlare. All services using "Bypass" access reference this single policy, keeping your Cloudflare dashboard clean.

### Zone Default Policies (*.tld Wildcards)

The second section shows **Zone Default Policies** - a security best practice feature that protects all subdomains:

*   **Protection Status:** Visual badges show which DNS zones have wildcard `*.domain.com` policies (Protected 🛡️) and which don't (Not Protected ⚠️).
*   **Create Zone Policy:** Click "Create Policy" on any unprotected zone to create a wildcard Access Application.
*   **Select Policy:** Choose which Access Group should protect all subdomains of the zone (can be public bypass, authentication, or any custom policy).
*   **Security Safety Net:** Even if you forget to add a policy to a specific service, the zone-level wildcard policy will catch it.

**Best Practice:** Create zone default policies for all your domains. For public-facing domains, use the default bypass policy. For internal/private domains, use an authentication policy. This ensures no subdomain is accidentally exposed.

For more details, see the [Access Policy Best Practices & Examples](Access-Policy-Best-Practices.md) guide.

## Settings Page

The Settings page contains various administrative and configuration options:

*   **Cloudflare Tunnels:** This section lists all the Cloudflare Tunnels found on your account, their status, and their connected `cloudflared` agents. You can also view all CNAME DNS records pointing to any of your tunnels.
*   **Backup & Restore:** Download a full DockFlare backup archive (`.zip`) containing encrypted config, agent keys, and state, or upload a previously exported archive to restore the instance.
*   **Security:**
    *   **Change Password:** Change your password for the Web UI.
    *   **Disable Password Login:** For advanced use cases where you place DockFlare behind another authentication proxy. **⚠️ Warning:** This creates a security risk due to Docker network exposure - any container on the same Docker network can bypass external authentication and access DockFlare's API directly. We strongly recommend using OAuth/OIDC providers instead for single sign-on convenience without sacrificing security. See [Accessing the Web UI](Accessing-the-Web-UI.md#disabling-password-login) for full security implications.
*   **Cloudflare Credentials:** Allows you to update your Cloudflare Account ID and API Token after the initial setup.
*   **Core Configuration:** Lets you change settings like the Tunnel Name and Rule Grace Period.
