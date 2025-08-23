# Access Policy Best Practices & Examples

DockFlare's most powerful security feature is **Access Groups**. They provide a centralized, reusable, and maintainable way to secure your services using Cloudflare Zero Trust.

## The "Golden Rule": Use Access Groups

The single most important best practice is to **use Access Groups for all your common access policies**.

Access Groups are policy templates you create in the DockFlare Web UI. Instead of defining complex rules with multiple labels on every container, you create a policy once and apply it with a single, clean label.

---

## How to Create and Use Access Groups

Creating an Access Group is a simple process done entirely within the DockFlare UI.

### Step 1: Create the Access Group

1.  Navigate to the **Access Policies** page from the main navigation bar in the DockFlare UI.
2.  Click the **"Add Access Group"** button.
3.  Give your group a **unique and descriptive ID**. This ID is what you will use in your Docker labels. For example: `admin-users`, `home-network`, `geo-block`.
4.  Define your policy rules. You can add multiple rules to a single group.
5.  Set the **Action** for the policy (e.g., `Allow`, `Block`).
6.  Save the group.

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
*   **Rule 1:**
    *   **Type:** `Email`
    *   **Value:** `user1@example.com`
*   **Rule 2:**
    *   **Type:** `Email`
    *   **Value:** `user2@example.com`
*   **Action:** `Allow`

This policy will require any user trying to access the service to log in, and only `user1@example.com` and `user2@example.com` will be granted access.

### Example 2: Allow Your Home IP Address

This policy restricts access to your home network, allowing you to access services without needing to log in when you are at home.

1.  **Find Your Public IP:** In your browser, search for "what is my ip". Your public IP address will be displayed (e.g., `203.0.113.55`).
2.  **Create the Access Group:**
    *   **Group ID:** `home-network`
    *   **Rule 1:**
        *   **Type:** `IP`
        *   **Value:** `203.0.113.55/32` (The `/32` CIDR notation means this rule applies only to this single IP address).
    *   **Action:** `Allow`

This policy will grant access to anyone coming from your specific home IP address.

### Example 3: Geo-Fencing (Blocking Multiple Countries)

This policy can be used to block traffic from a list of specific countries, while allowing traffic from everywhere else.

*   **Group ID:** `geo-block`
*   **Rule 1: Block List**
    *   **Type:** `Country`
    *   **Value:** `RU, CN, KP` (Enter multiple country codes, separated by commas).
    *   **Action:** `Block`
*   **Rule 2: Allow Everyone Else**
    *   **Type:** `Everyone`
    *   **Action:** `Allow`

This policy will explicitly block users from Russia, China, and North Korea, while allowing users from all other countries to access the service. You can then combine this with an authentication policy by applying multiple groups (e.g., `dockflare.access.groups=geo-block,admin-users`).
