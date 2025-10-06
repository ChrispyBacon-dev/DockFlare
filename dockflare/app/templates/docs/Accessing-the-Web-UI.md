# Accessing the Web UI

Once you have successfully started the DockFlare container, you can access the web UI to manage your settings, view the status of your tunnels, and manually configure ingress rules.

## Default URL

By default, the DockFlare web UI is accessible on port `5000`. To access it, open your web browser and navigate to the following URL:

```
http://<your-server-ip>:5000
```

Replace `<your-server-ip>` with the IP address of the server where DockFlare is running.

## First-Time Setup

The first time you access the web UI, you will be guided by the **Pre-Flight Setup Wizard**. This wizard helps you:

1.  Restore from an existing DockFlare backup archive (`dockflare_backup_*.zip`). If you choose this option, the system imports your encrypted configuration, state, and agent keys, then automatically restarts the container to apply them.
2.  Create an administrator account and password for the web UI.
3.  Provide your Cloudflare Account ID, Zone ID (optional), and API token.
4.  Confirm tunnel settings and finish the onboarding steps.

## Logging In

After the initial setup, you will be presented with a login screen every time you access the web UI. Use the password you created during the setup process to log in.

## Disabling Password Login

DockFlare includes a "Disable Password Login" setting intended for advanced deployments where DockFlare itself is protected by an external authentication layer (like Cloudflare Access). **We strongly advise against using this feature** for most deployments.

### Why this setting exists

If you run DockFlare behind Cloudflare Access or another authentication proxy that enforces SSO before reaching the application, you can disable DockFlare's built-in password login to avoid double authentication.

### Security risks when enabled

- ⚠️ **All API endpoints become accessible without authentication** when this setting is enabled
- ⚠️ **Docker network exposure:** Even if DockFlare is behind Cloudflare Access on the public internet, containers on the same Docker network can bypass external authentication and access DockFlare's API directly
- ⚠️ **No authentication enforcement:** The application assumes external authentication is handling security

### Attack vector example

```
Internet → Cloudflare Access (Protected) → DockFlare ✅
         ↓
Docker Network → Other Container → DockFlare API (Unprotected) ❌
```

Even when DockFlare is protected by Cloudflare Access from the internet, any container running on the same Docker network can bypass that protection and directly access DockFlare's API endpoints without authentication.

### Recommended approach

Instead of disabling password authentication, use one of these secure options:

1. **Local DockFlare credentials** - Simple password authentication built into DockFlare
2. **OAuth/OIDC providers** - Configure Google, GitHub, Azure AD, or other identity providers for easy single sign-on without sacrificing security (see [OAuth Provider Setup](OAuth-Provider-Setup.md))

Both options provide proper authentication while maintaining the convenience of SSO. The OAuth option gives you the single sign-on experience without the security risks of disabled authentication.

### Bottom line

Unless you have a very specific, well-understood security architecture with network isolation, keep password login enabled and use OAuth for convenience.
