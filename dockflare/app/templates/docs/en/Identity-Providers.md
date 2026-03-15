# Identity Providers

> **📌 Important:** This guide is for configuring **Identity Providers for Cloudflare Access Policies** to protect your services/applications. If you want to configure OAuth/OIDC for **DockFlare Web UI login**, see [OAuth Provider Setup](help/OAuth-Provider-Setup.md) instead.

Identity Providers (IdPs) enable OAuth/OIDC authentication for your Cloudflare Zero Trust protected applications. DockFlare makes it easy to manage IdPs and integrate them into your access policies.

## Overview

Instead of relying solely on email-based authentication, you can use popular OAuth providers like Google, GitHub, Azure AD, and more. Users authenticate through their existing accounts, providing a seamless and secure login experience.

## Supported Providers

DockFlare supports the following identity providers:

- **Google** - Consumer Google accounts
- **Google Workspace** - Google Workspace (G Suite) accounts with optional domain restriction
- **Microsoft Azure AD** - Microsoft Entra ID (Azure Active Directory)
- **Okta** - Okta Identity Cloud
- **GitHub** - GitHub OAuth
- **Generic OpenID Connect** - Any OIDC-compliant provider

## Managing Identity Providers

### Adding an Identity Provider

1. Navigate to **Access Policies** page
2. In the **Identity Providers** section, click **Add Provider**
3. Fill in the required fields:
   - **Friendly Name**: Internal name for DockFlare (e.g., `google-main`, `github-dev`)
   - **Display Name**: Name shown in Cloudflare dashboard
   - **Provider Type**: Select your OAuth provider
   - **Configuration**: Provider-specific credentials (see setup guides below)
4. Click **Create Provider**
5. Test the provider using the provided test URL

### Syncing from Cloudflare

If you've already configured IdPs in Cloudflare Zero Trust:

1. Click **Sync from Cloudflare** in the Identity Providers section
2. DockFlare will import all existing IdPs and auto-generate friendly names
3. You can rename the friendly names for easier reference in labels

### Testing an Identity Provider

After creating an IdP, you can test it:

1. Click the **⋮** menu next to the provider
2. Select **Test IdP**
3. A new window opens where you can authenticate
4. Verify the login flow works correctly

## Provider Setup Guides

### Google (Consumer Accounts)

**Step 1: Create OAuth Credentials**

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select an existing one
3. Navigate to **APIs & Services** → **Credentials**
4. Click **Create Credentials** → **OAuth client ID**
5. Select **Web application**
6. Add authorized redirect URI:
   ```
   https://<your-team>.cloudflareaccess.com/cdn-cgi/access/callback
   ```
   <small>You can find your team name in <a href="https://one.dash.cloudflare.com/{{ACCOUNT_ID}}/settings/custom_pages" target="_blank">Zero Trust</a> by going to Settings > Custom Pages.</small>
7. Copy the **Client ID** and **Client Secret**

**Step 2: Configure in DockFlare**

- **Client ID**: Paste from Google Cloud Console
- **Client Secret**: Paste from Google Cloud Console

---

### Google Workspace

Same as Google setup above, with an additional optional field:

- **Apps Domain**: (Optional) Restrict to specific domain (e.g., `example.com`)

If specified, only users with `@example.com` email addresses can authenticate.

---

### Microsoft Azure AD

**Step 1: Register Application in Azure**

1. Go to [Azure Portal](https://portal.azure.com/)
2. Navigate to **Azure Active Directory** → **App registrations**
3. Click **New registration**
4. Name your application (e.g., "DockFlare Access")
5. Under **Redirect URI**, select **Web** and enter:
   ```
   https://<your-team>.cloudflareaccess.com/cdn-cgi/access/callback
   ```
   <small>You can find your team name in <a href="https://one.dash.cloudflare.com/{{ACCOUNT_ID}}/settings/custom_pages" target="_blank">Zero Trust</a> by going to Settings > Custom Pages.</small>
6. Click **Register**
7. Copy the **Application (client) ID**
8. Copy the **Directory (tenant) ID**
9. Go to **Certificates & secrets** → **New client secret**
10. Create a secret and copy the **Value**

**Step 2: Configure in DockFlare**

- **Application (client) ID**: Paste from Azure
- **Directory (tenant) ID**: Paste from Azure
- **Client Secret**: Paste from Azure

---

### GitHub

**Step 1: Create OAuth App**

1. Go to [GitHub Developer Settings](https://github.com/settings/developers)
2. Click **New OAuth App**
3. Fill in the details:
   - **Application name**: DockFlare Access
   - **Homepage URL**: `https://your-domain.com`
   - **Authorization callback URL**:
     ```
     https://<your-team>.cloudflareaccess.com/cdn-cgi/access/callback
     ```
     <small>You can find your team name in <a href="https://one.dash.cloudflare.com/{{ACCOUNT_ID}}/settings/custom_pages" target="_blank">Zero Trust</a> by going to Settings > Custom Pages.</small>
4. Click **Register application**
5. Copy the **Client ID**
6. Click **Generate a new client secret** and copy it

**Step 2: Configure in DockFlare**

- **Client ID**: Paste from GitHub
- **Client Secret**: Paste from GitHub

---

### Okta

**Step 1: Create Application in Okta**

1. Log in to your [Okta Admin Console](https://admin.okta.com/)
2. Navigate to **Applications** → **Create App Integration**
3. Select **OIDC - OpenID Connect**
4. Choose **Web Application**
5. Configure:
   - **Sign-in redirect URIs**:
     ```
     https://<your-team>.cloudflareaccess.com/cdn-cgi/access/callback
     ```
     <small>You can find your team name in <a href="https://one.dash.cloudflare.com/{{ACCOUNT_ID}}/settings/custom_pages" target="_blank">Zero Trust</a> by going to Settings > Custom Pages.</small>
6. Click **Save**
7. Copy the **Client ID** and **Client Secret**
8. Note your **Okta domain** (e.g., `https://dev-12345.okta.com`)

**Step 2: Configure in DockFlare**

- **Okta Account URL**: Your Okta domain (e.g., `https://dev-12345.okta.com`)
- **Client ID**: Paste from Okta
- **Client Secret**: Paste from Okta

---

### Generic OpenID Connect

For any OIDC-compliant provider:

**Step 1: Get Provider Configuration**

From your IdP's documentation, obtain:
- Authorization URL
- Token URL
- JWKS URL (JSON Web Key Set)
- Client ID
- Client Secret

**Step 2: Configure in DockFlare**

- **Authorization URL**: Provider's OAuth authorization endpoint
- **Token URL**: Provider's token endpoint
- **JWKS URL**: Provider's JWKS endpoint (for signature verification)
- **Client ID**: From your provider
- **Client Secret**: From your provider

---

## Using Identity Providers in Access Policies

### In Access Groups

1. Navigate to **Access Policies** → **Advanced Access Policies**
2. Click **Create New Group** or edit an existing group
3. In the **Policy Rules** section:
   - **Identity Providers**: Select one or more IdPs
   - **Allowed Emails or Domains**: **Required when using IdPs** - Specify allowed email addresses
4. Save the group

### Authentication Modes

You have two options:

1. **Email Only**: Enter emails, don't select any IdPs - users authenticate via one-time PIN
2. **IdP + Email (Required)**: Select IdP(s) AND enter allowed emails - users must authenticate via the selected IdP AND be in the allowed email list

**⚠️ Security Notice**: When using Identity Providers, you **must** specify allowed email addresses. This prevents unauthorized access - for example, without email restrictions, selecting "Google" as an IdP would allow anyone with any Google account to access your service.

### In Docker Labels

Use the friendly name in your container labels:

```yaml
services:
  myapp:
    image: myapp:latest
    labels:
      dockflare.enable: "true"
      dockflare.hostname: "app.example.com"
      dockflare.access.group: "my-access-group"
```

The access group `my-access-group` will resolve IdP friendly names to Cloudflare UUIDs automatically.

---

## Best Practices

### Naming Conventions

Use descriptive friendly names:
- ✅ `google-main`, `github-dev`, `azure-work`
- ❌ `idp1`, `test`, `new`

### Security

- **Rotate Secrets Regularly**: Update client secrets periodically
- **Limit Scope**: For Google Workspace and Azure AD, restrict to specific domains when possible
- **Test Before Production**: Always test IdPs before applying to production services
- **Monitor Usage**: Review Cloudflare logs to detect unauthorized access attempts

### Multiple Environments

Create separate IdPs for different environments:
- `google-dev` - Development environment
- `google-staging` - Staging environment
- `google-prod` - Production environment

### Email Requirements with IdPs

**IMPORTANT**: IdP authentication always requires email restrictions for security.

**Example Access Group:**
- **Identity Providers**: `google-main`
- **Allowed Emails**: `admin@example.com, user@example.com, @contractor-domain.com`

This configuration allows access to users who:
- Authenticate via the `google-main` IdP (Google OAuth) **AND**
- Have an email address matching one of: `admin@example.com`, `user@example.com`, or any `@contractor-domain.com` email

**How it works:**
1. User clicks sign-in on your protected application
2. Redirected to Google OAuth login
3. After Google authentication, Cloudflare checks if their email is in the allowed list
4. Access granted only if email matches the allowed list

---

## Troubleshooting

### "Invalid Redirect URI" Error

**Cause**: Redirect URI in OAuth provider doesn't match Cloudflare's expected URI.

**Solution**: Ensure you've added the exact redirect URI:
```
https://<your-team>.cloudflareaccess.com/cdn-cgi/access/callback
```
<small>You can find your team name in <a href="https://one.dash.cloudflare.com/{{ACCOUNT_ID}}/settings/custom_pages" target="_blank">Zero Trust</a> by going to Settings > Custom Pages.</small>

Replace `<your-team>` with your Cloudflare Zero Trust team name.

---

### "IdP Test Failed"

**Cause**: Incorrect credentials or configuration.

**Solution**:
1. Verify Client ID and Client Secret are correct
2. Check that the OAuth application is enabled in your provider
3. For Azure AD, verify both client ID and tenant ID are correct
4. Test the provider using Cloudflare's test URL

---

### "Cannot Delete System-Managed IdP"

**Cause**: Trying to delete the built-in One-Time PIN provider.

**Solution**: The `onetimepin` provider is system-managed and cannot be deleted. It's required for email-based OTP authentication.

---

### "IdP Not Found in Docker Label"

**Cause**: Using Cloudflare UUID instead of friendly name in label.

**Solution**: Use the friendly name (e.g., `google-main`) instead of the UUID in your access group configuration.

---

## Related Documentation

- [Access Policy Best Practices](Access-Policy-Best-Practices.md)
- [Zone Default Policies](Zone-Default-Policies.md)
- [Container Labels](Container-Labels.md)
- [Security Architecture](Security-Architecture.md)

---

## Additional Resources

- [Cloudflare Zero Trust Documentation](https://developers.cloudflare.com/cloudflare-one/)
- [OAuth 2.0 Specification](https://oauth.net/2/)
- [OpenID Connect Documentation](https://openid.net/connect/)
