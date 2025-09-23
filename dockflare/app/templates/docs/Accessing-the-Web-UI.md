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

For advanced use cases, such as placing the DockFlare dashboard behind another authentication proxy (like Cloudflare Access), you can disable the built-in password login. This option is available in the **Settings** page under the **Security** section.

**Warning:** Disabling password login will make your DockFlare dashboard publicly accessible. Only do this if you have another authentication method in place.
