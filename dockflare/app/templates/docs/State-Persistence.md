# State Persistence

DockFlare is a stateful application. It needs to keep track of the services it manages, UI overrides, and other configuration details. This state is persisted to disk to ensure that your configuration is not lost if the DockFlare container is restarted or recreated.

## How State is Stored

DockFlare stores its state in two main files located in the `/app/data` directory inside the container:

1.  `dockflare_config.dat`: This is the most critical file. It contains all your core settings and sensitive information in an **encrypted** format. This includes:
    *   Your Cloudflare API Token and Account ID.
    *   Your DockFlare UI password hash.
    *   Core settings configured through the UI, such as the Tunnel Name and Zone IDs.

2.  `state.json`: This file stores the dynamic state of your managed services in a plain JSON format. This includes:
    *   The list of all ingress rules DockFlare is managing, whether they come from Docker labels or were created manually in the UI.
    *   Any UI overrides applied to access policies.
    *   All Access Groups you have created.
    *   The "pending deletion" status for services that have been stopped but are still within their grace period.

## The Importance of a Persistent Volume

Because all of your configuration is stored in the `/app/data` directory, it is **absolutely crucial** that you map this directory to a persistent volume on your host machine.

If you do not use a persistent volume, **all your settings, UI password, and rule configurations will be lost** every time the DockFlare container is removed and recreated (e.g., when you update the image).

### Recommended Docker Compose Configuration

The recommended `docker-compose.yml` configuration handles this for you automatically by defining a named volume and mounting it to `/app/data`:

```yaml
services:
  dockflare:
    # ... other settings
    volumes:
      # This line ensures your data is persisted
      - ./dockflare_data:/app/data

volumes:
  # This defines the named volume on your host
  dockflare_data:
```

With this configuration, your `dockflare_config.dat` and `state.json` files will be stored in a directory named `dockflare_data` on your host, safely preserving your setup across container updates.

## Backup and Restore

The `state.json` file can be backed up and restored. The DockFlare UI provides a "Backup & Restore" feature on the **Settings** page that allows you to download a copy of your `state.json` and upload it to restore your configuration.

**Note:** The backup and restore feature only includes the `state.json` file. It does **not** include the encrypted `dockflare_config.dat` file. To fully back up your DockFlare instance, you should back up the entire `/app/data` directory.
