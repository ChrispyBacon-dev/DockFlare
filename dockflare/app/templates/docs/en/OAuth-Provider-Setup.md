## OAuth Provider Setup

> **📌 Important:** This guide is for configuring **DockFlare Web UI authentication** (logging into DockFlare itself). If you want to configure OAuth/OIDC for **Cloudflare Access Policies** to protect your services, see [Identity Providers](help/Identity-Providers.md) instead.

DockFlare allows you to delegate user authentication to external providers using the OpenID Connect (OIDC) standard. This enables single sign-on (SSO) for the DockFlare web interface and allows you to integrate with identity providers like Google, Authentik, Okta, and more.

### Adding a New Provider

Follow these steps to add a new OIDC provider:

1.  **Navigate to Settings:** From the main dashboard, go to the **Settings** page.
2.  **Locate OAuth Section:** Scroll down to the **OAuth Authentication** section.
3.  **Add Provider:** Click the **Add Provider** button to open the configuration modal.

You will be presented with the following fields:

*   **Provider Type:** This is set to `OpenID Connect (OIDC)`, the modern standard for federated authentication.
*   **Issuer URL:** This is the most important field. It is the base URL of your OIDC provider, which DockFlare uses to automatically discover the provider's configuration. For example, `https://accounts.google.com` or `https://authentik.yourdomain.com/application/o/dockflare/`.
*   **Provider ID:** A short, unique, lowercase name for this provider (e.g., `google`, `authentik-corp`). This ID is used internally and in the callback URL.
*   **Display Name:** The user-friendly name that will appear on the login button (e.g., `Google`, `Corporate SSO`).
*   **Client ID:** The public identifier for the DockFlare application, which you will get from your OIDC provider's developer console.
*   **Client Secret:** The confidential secret for the DockFlare application, also from your OIDC provider's console.
*   **Enable Provider:** This checkbox allows you to enable or disable the provider at any time.

After filling in the details, click **Add Provider** to save.

### Finding Your Callback URL

Once you have added a provider, the required **Callback URL** (also known as an "Authorized redirect URI") will be displayed under the provider's entry on the Settings page.

You must copy this exact URL and add it to your provider's list of allowed callback URLs in their administration console.

---

### Example: Setting up Google

Here is a quick guide to configuring Google as an OAuth provider.

1.  **Go to Google Cloud Console:** Navigate to the [APIs & Services > Credentials](https://console.cloud.google.com/apis/credentials) page.
2.  **Create Credentials:** Click **+ CREATE CREDENTIALS** and select **OAuth client ID**.
3.  **Configure Application:**
    *   Set the **Application type** to **Web application**.
    *   Give it a name (e.g., "DockFlare").
4.  **Add Redirect URI:**
    *   Under **Authorized redirect URIs**, click **+ ADD URI**.
    *   Enter the callback URL provided by DockFlare. It will look like this: `https://your-dockflare-domain.com/auth/google/callback`.
5.  **Create and Copy:** Click **CREATE**. A window will appear showing your **Client ID** and **Client Secret**. Copy these values.
6.  **Configure in DockFlare:**
    *   **Issuer URL:** `https://accounts.google.com`
    *   **Provider ID:** `google`
    *   **Display Name:** `Google`
    *   **Client ID:** `(Your Client ID from Google)`
    *   **Client Secret:** `(Your Client Secret from Google)`

Save the provider in DockFlare, and you will be able to log in with your Google account.

---

### Configuring DockFlare with OAuth and Access Policies

When using OAuth authentication, you may want to protect your main DockFlare interface with access policies while ensuring OAuth callbacks work properly. This is especially important if you have IP restrictions or other access controls on your DockFlare instance.

#### **Best Practice: Bypass Policy for OAuth Callbacks**

Use indexed labels to create separate rules for your main interface and OAuth callback paths:

```yaml
services:
  dockflare:
    image: alplat/dockflare:stable
    labels:
      # Main DockFlare interface with access policy
      - "dockflare.enable=true"
      - "dockflare.hostname=dockflare.example.com"
      - "dockflare.service=http://dockflare:5000"
      - "dockflare.access.group=team"  # your custom access policy

      # OAuth callback paths with bypass policy (required for OAuth to work)
      - "dockflare.0.hostname=dockflare.example.com"
      - "dockflare.0.path=/auth/google/callback"
      - "dockflare.0.service=http://dockflare:5000"
      - "dockflare.0.access.policy=bypass"

      # Add additional callback paths for other providers if needed
      - "dockflare.1.hostname=dockflare.example.com"
      - "dockflare.1.path=/auth/github/callback"
      - "dockflare.1.service=http://dockflare:5000"
      - "dockflare.1.access.policy=bypass"
```

#### **Why This Configuration is Needed**

- **Main Interface Protection**: Your DockFlare dashboard remains protected by your chosen access policy
- **OAuth Functionality**: OAuth callbacks can reach DockFlare without authentication barriers
- **Security**: Only specific callback paths are bypassed, not the entire application
- **Flexibility**: Works with any combination of access policies (IP-based, authentication-based, etc.)

#### **Important Notes**

1. **Path Matching**: The callback path must exactly match what your OAuth provider expects
2. **Multiple Providers**: Add a separate indexed rule for each OAuth provider you configure
3. **No Wildcards**: Avoid using wildcard paths for security reasons - be specific with callback URLs
4. **Testing**: After configuration, test both protected access (main interface) and OAuth login flows
