# Access Policy Best Practices & Examples

DockFlare's most powerful security feature is **Access Groups**. They provide a centralized, reusable, and maintainable way to secure your services using Cloudflare Zero Trust.

## The "Golden Rule": Use Access Groups

The single most important best practice is to **use Access Groups for all your common access policies**.

Access Groups are policy templates you create in the DockFlare Web UI. Instead of defining complex rules with multiple labels on every container, you create a policy once and apply it with a single, clean label. DockFlare v3.0.3 now syncs every group to a reusable Cloudflare Access Policy so the same decision set can serve multiple applications.

---

## How to Create and Use Access Groups

Creating an Access Group is a simple process done entirely within the DockFlare UI.

### Step 1: Create the Access Group

1.  Navigate to the **Access Policies** page from the main navigation bar in the DockFlare UI.
2.  Click the **"Add Access Group"** button.
3.  Give your group a **unique and descriptive ID**. This ID is what you will use in your Docker labels. For example: `admin-users`, `home-network`, `geo-block`.
4.  Pick the **Access Mode** from the tabs at the top of the modal:
    *   **Authenticated** requires users to sign in and emits an `allow` decision.
    *   **Public** uses a `bypass` decision so the application stays open while still honouring geo filters.
5.  Fill in the inputs that appear for the selected mode (emails for Authenticated, optional country list for both).
6.  Adjust optional settings like session duration, App Launcher visibility, and automatic IdP redirect if you are in Authenticated mode.
7.  Save the group. DockFlare writes the definition locally and syncs it to Cloudflare as `DockFlare-AccessGroup-<id>`.

### Step 2: Apply the Access Group

Once created, you have two ways to apply your Access Group to a service:

#### A) With a Docker Label (The Recommended Way)

For any new or existing container, simply add the `dockflare.access.group` label with the ID of the group you created.

```yaml
services:
  grafana:
    image: grafana/grafana
    labels:
      - "dockflare.enable=true"
      - "dockflare.hostname=monitoring.example.com"
      - "dockflare.service=http://grafana:3000"
      # Apply the entire policy with one simple label:
      - "dockflare.access.group=admin-users"
```
You can also apply multiple groups by using `dockflare.access.groups` with a comma-separated list of IDs:
`dockflare.access.groups=admin-users,home-network`

#### System-Managed Policies

DockFlare provides two built-in system policies that are automatically available:

- **`public-default-bypass`** - Public access with bypass decision (use for truly public services)
- **`authenticated-default`** - Default authentication with one-time PIN + email restriction

These system policies are non-deletable and serve as the foundation for zone protection and legacy label migration.

#### B) Via the Web UI (For Manual Rules or Overrides)

You can also apply an Access Group to any rule directly from the dashboard:
1.  Find the ingress rule you want to modify on the main dashboard.
2.  Click the **"Manage Rule"** button.
3.  In the editing modal, select your desired Access Group(s) from the "Access Groups" dropdown menu.
4.  Save the changes.

This is perfect for applying policies to manually created rules (for non-Docker services) or for temporarily overriding a policy defined by Docker labels.

---

## Policy Examples

Here are some common policy configurations you can create within an Access Group.

### Example 1: Authenticate by Email

This is the most common use case: allowing only specific users who can authenticate with your configured Identity Provider (e.g., Google, GitHub, or a one-time PIN sent to their email).

*   **Group ID:** `admin-users`
*   **Mode:** *Authenticated*
*   **Allowed emails:** `user1@example.com`, `user2@example.com`
*   **Session duration:** `24h`

DockFlare creates a reusable policy with an `allow` decision for the listed emails and a fall-through `deny` rule for everyone else. Apply the group with `dockflare.access.group=admin-users`.

### Example 2: Allow Your Home IP Address

This policy restricts access to your home network, allowing you to skip the login prompt when you are on a trusted IP while enforcing authentication elsewhere.

1.  **Find Your Public IP:** In your browser, search for "what is my ip". Your public IP address will be displayed (e.g., `203.0.113.55`).
2.  **Create the Access Group:**
    *   **Group ID:** `home-network`
    *   **Mode:** *Authenticated*
    *   **Allowed emails:** `you@example.com`
    *   **Bypass IPs:** add `203.0.113.55/32` to the IP allowlist field

DockFlare generates a policy that first bypasses your IP range and then requires the listed emails to authenticate. Everyone else receives a deny decision.

### Example 3: Geo-Fencing (Blocking Multiple Countries)

This policy keeps your marketing site public while limiting traffic from specific regions.

*   **Group ID:** `public-eu`
*   **Mode:** *Public*
*   **Blocked countries:** `RU`, `CN`, `KP`

The resulting reusable policy issues a Cloudflare `bypass` decision for everyone, excluding the listed countries. Combine it with other groups if you need to layer additional controls (`dockflare.access.groups=public-eu,admin-users`).

---

## Zone Default Policies - Security Best Practice

### What Are Zone Default Policies?

Zone Default Policies are wildcard `*.domain.com` Access Applications that protect ALL subdomains of a DNS zone, including ones you haven't explicitly configured yet.

### Why You Need Them

**The Problem:** If you forget to add an Access policy to a service, it's exposed publicly by default.

**The Solution:** A zone-level wildcard policy acts as a safety net. Even if you forget to configure `forgotten-service.yourdomain.com`, the `*.yourdomain.com` policy will catch it.

### How to Set Them Up

1. Navigate to **Access Policies** page
2. Scroll to **Zone Default Policies (*.tld Wildcards)** section
3. Look for zones with "Not Protected" ⚠️ badge
4. Click **Create Policy**
5. Select appropriate access group:
   - **For public domains:** Use `public-default-bypass`
   - **For internal domains:** Use an authentication policy
   - **For mixed-use:** Use your most restrictive policy

### Best Practices

- ✅ **Always create zone policies** for production domains
- ✅ **Use authentication policies** for internal/private zones
- ✅ **Use public bypass** only for truly public zones
- ✅ **Review regularly** - check zone protection status monthly
- ⚠️ **Remember priority** - Specific hostname policies override wildcard policies

### Policy Priority Order

Cloudflare evaluates Access policies in this order:

1. **Exact hostname match** (e.g., `app.example.com`) - Highest priority
2. **Wildcard match** (e.g., `*.example.com`) - Fallback
3. **No match** = Public access (no Access App) - Default

This means you can have a restrictive zone default policy and still create specific exceptions for individual services.

---

## Managing External Cloudflare Policies

### Understanding Policy Types

DockFlare displays three types of policies in the Access Policies page, each with a visual badge:

- **🟦 DockFlare** - Policies created and managed by DockFlare (prefix: `DockFlare-`)
- **🟪 External** - Policies created outside DockFlare (manual or other tools)
- **🟧 System** - Non-deletable system policies (`public-default-bypass`, `authenticated-default`)

### Syncing External Policies

By default, DockFlare only imports policies with the `DockFlare-` prefix. This keeps your policy list clean and focused on container infrastructure.

**To sync ALL Cloudflare policies** (including those created manually):

1. Set the environment variable: `SYNC_ALL_CLOUDFLARE_POLICIES=true`
2. Restart DockFlare
3. Click **"Sync from Cloudflare"** on the Access Policies page

External policies will appear with a purple **"External"** badge.

### Why Import External Policies?

**Pros:**
- Complete visibility of your entire Cloudflare Access setup
- Reuse existing policies without recreating them
- Centralized management in one interface
- Apply any policy to any service (DockFlare-managed or not)

**Cons:**
- Longer policy list if you have many external policies
- Risk of accidentally modifying policies used by non-DockFlare services

### Organizing Your Policies

**Pro Tip:** Rename external policies in Cloudflare to use the `DockFlare-` prefix

You can organize external policies by renaming them in the Cloudflare dashboard:

1. Open the policy in **Cloudflare Zero Trust**
2. Rename it to use `DockFlare-` prefix (e.g., `DockFlare-LegacyVPN` or `DockFlare-ThirdPartyApp`)
3. Click **"Sync from Cloudflare"** in DockFlare
4. The policy now appears as a **DockFlare-managed** policy (blue badge)

This allows you to:
- ✅ Group all DockFlare-visible policies with consistent naming
- ✅ Filter and sort policies by type
- ✅ Distinguish "managed by DockFlare" from "just visible in DockFlare"

### Filtering Policies

Use the **Filter** dropdown to view specific policy types:

- **All Policies** - Shows everything (DockFlare, External, System)
- **DockFlare-Managed** - Shows only blue-badged policies
- **External** - Shows only purple-badged policies
- **System** - Shows only system policies

### Safety Features

**External Policy Protection:**

When deleting or editing external policies, DockFlare displays a warning:

> ⚠️ WARNING: This is an EXTERNAL policy not created by DockFlare.
>
> Modifying this policy may affect services outside of DockFlare.
>
> Are you absolutely sure?

This prevents accidental changes to policies managed by other tools or manual configurations.

### Best Practices

1. **Default Setup (Recommended):**
   - Keep `SYNC_ALL_CLOUDFLARE_POLICIES=false` (default)
   - Only DockFlare-managed policies appear
   - Clean, focused policy list

2. **Advanced Setup (Power Users):**
   - Enable `SYNC_ALL_CLOUDFLARE_POLICIES=true`
   - View and manage ALL policies in one place
   - Rename external policies to `DockFlare-` prefix for organization

3. **Hybrid Approach:**
   - Keep sync disabled by default
   - Manually rename important external policies to `DockFlare-*` in Cloudflare
   - They'll automatically appear after next sync

4. **Policy Naming Convention:**
   ```
   DockFlare-AccessGroup-<id>     # Auto-generated by access groups
   DockFlare-<custom-name>         # Your renamed external policies
   <anything-else>                 # Pure external (only visible if sync enabled)
   ```
