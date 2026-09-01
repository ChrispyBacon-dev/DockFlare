# Discord Notifications and Apprise API

This guide configures a Discord channel to receive DockFlare notifications. It covers two supported designs:

1. Paste the Discord webhook directly into DockFlare. Nothing else needs to be installed.
2. Deploy the optional Apprise API, store Discord there, and connect DockFlare to that stored configuration.

The first setup is recommended when DockFlare is the only application sending notifications. Apprise is already bundled inside the DockFlare container and recognizes the normal Discord webhook URL. The API setup is useful when several applications should share destinations or when notification configuration should be managed centrally.

Apprise is an independent third-party open-source project. It is not developed or operated by DockFlare. Notifications remain disabled until you explicitly configure and enable them.

## Before you begin

You need:

- permission to manage webhooks in the target Discord server;
- a Discord text channel for DockFlare messages;
- access to DockFlare's **Settings** page; and
- Docker with Compose if you choose the self-hosted Apprise API setup.

Never post a real webhook URL, configuration key, or Apprise destination in an issue, screenshot, chat, or log. The examples below use placeholders.

## Step 1: Create a Discord webhook

1. Open the Discord server.
2. Open **Server Settings**.
3. Select **Integrations**.
4. Select **Webhooks**.
5. Create a webhook.
6. Name it `DockFlare` and select the channel that should receive notifications.
7. Select **Copy Webhook URL**.

The copied URL has this structure:

```text
https://discord.com/api/webhooks/{WEBHOOK_ID}/{WEBHOOK_TOKEN}
```

The ID and token authorize anyone holding the URL to post to the selected channel. Store it as a secret. If it is exposed, delete or regenerate the webhook in Discord.

## Option A: Paste the Discord webhook into DockFlare

This is the simplest setup. No Apprise installation or additional container is required.

Paste the complete webhook copied from Discord into DockFlare without changing it:

```text
https://discord.com/api/webhooks/{WEBHOOK_ID}/{WEBHOOK_TOKEN}
```

For example:

```text
https://discord.com/api/webhooks/123456789012345678/REPLACE_WITH_THE_REAL_TOKEN
```

Apprise also supports its explicit Discord URL format, but converting the webhook is optional:

```text
discord://123456789012345678/REPLACE_WITH_THE_REAL_TOKEN
```

Then continue with [Configure DockFlare](#configure-dockflare).

## Option B: Deploy a self-hosted Apprise API

The Apprise API provides a web interface and persistent configuration store. DockFlare sends to the API, and the API forwards the notification to Discord.

The data flow is:

```text
DockFlare -> Apprise API -> Discord webhook -> Discord channel
```

### Create the deployment directory

Run these commands on the Docker host that will run Apprise:

```bash
mkdir -p apprise/config
cd apprise
```

Create `docker-compose.yml` with the following content:

```yaml
services:
  apprise:
    image: caronc/apprise:latest
    container_name: apprise
    restart: unless-stopped
    user: "${PUID:-1000}:${PGID:-1000}"
    ports:
      - "8000:8000"
    environment:
      APPRISE_STATEFUL_MODE: simple
      APPRISE_WORKER_COUNT: "1"
      APPRISE_ADMIN: "y"
      TZ: ${TZ:-UTC}
    volumes:
      - ./config:/config
    networks:
      - cloudflare-net

networks:
  cloudflare-net:
    external: true
```

Create a `.env` file beside `docker-compose.yml` and set the user, group, and timezone for your Docker host:

```dotenv
PUID=1000
PGID=1000
TZ=Europe/Zurich
```

Use `id -u` and `id -g` on the host to find the correct numeric values. The example uses DockFlare's existing external `cloudflare-net` network so the DockFlare container can reach the API by its service name.

If your DockFlare deployment uses a different shared network, replace `cloudflare-net` with that network. If Apprise runs on another host, the shared Docker network is not required and DockFlare must use a reachable hostname or IP address instead.

If the external network does not exist yet, create it before starting the stack:

```bash
docker network create cloudflare-net
```

### Start Apprise API

```bash
docker compose pull
docker compose up -d
```

Open the web interface:

```text
http://{APPRISE_HOST}:8000
```

You can also verify the API status at:

```text
http://{APPRISE_HOST}:8000/status
```

This Compose example is intended for a trusted local network. Do not expose the administrative interface directly to the public internet. Use firewall restrictions or a properly authenticated HTTPS reverse proxy if remote administration is required.

### Create a persistent configuration

1. Open the Apprise API web interface.
2. Open the configuration manager.
3. Create a persistent configuration.
4. Note the configuration key shown by Apprise. It appears in an address resembling `/cfg/{CONFIG_KEY}`.
5. Add the Discord destination:

```text
discord://{WEBHOOK_ID}/{WEBHOOK_TOKEN}
```

6. Save the configuration.
7. Use Apprise's test function and confirm exactly one message reaches the Discord channel.

The configuration is stored below the local `./config` directory mounted at `/config` in the container. Include this directory in your normal backup process and protect it because it contains notification secrets.

### Build the URL for DockFlare

The address visible in your browser is not the destination to paste into DockFlare.

Do not use:

```text
http://{APPRISE_HOST}:8000/cfg/{CONFIG_KEY}#overview
```

Use the Apprise API plugin URL shown on the configuration overview. Its format is:

```text
apprise://{APPRISE_HOST}:8000/{CONFIG_KEY}
```

Choose the host according to your deployment:

| Deployment | DockFlare destination example |
|---|---|
| Apprise and DockFlare share a Docker network | `apprise://apprise:8000/{CONFIG_KEY}` |
| Apprise runs on another reachable host | `apprise://192.0.2.10:8000/{CONFIG_KEY}` |
| Apprise is behind an HTTPS reverse proxy | `apprises://notify.example.com/{CONFIG_KEY}` |

`apprise://` uses HTTP. `apprises://` uses HTTPS.

Do not use `localhost` or `127.0.0.1` when Apprise is a separate container. From inside the DockFlare container, those addresses refer to DockFlare itself.

Treat the complete API plugin URL as a secret because its configuration key can trigger every destination stored under that key.

## Configure DockFlare

1. Open DockFlare.
2. Go to **Settings > Notifications**.
3. Paste one destination into **Replacement Apprise URLs**:
   - Option A: `https://discord.com/api/webhooks/{WEBHOOK_ID}/{WEBHOOK_TOKEN}`
   - Option B: `apprise://apprise:8000/{CONFIG_KEY}` or the equivalent URL for your deployment
4. Select the notification events you want to receive.
5. Enable notifications.
6. Select **Save notification settings**.
7. Select **Send test notification**.
8. Wait for DockFlare to report successful delivery.
9. Confirm exactly one test message appears in Discord.

The replacement field is empty after every page load. This is intentional. Leaving it empty preserves the saved destination. Entering a value replaces the complete destination list.

## Recommended event selection

A useful starting point is:

- Cloudflare tunnel, DNS, and Access failures
- Docker listener stopped
- Agent enrollment failed
- Agent offline and recovered
- Agent decommission completed, failed, and timed out
- Tunnel down and recovered
- Rule deleted

Enable rule activation, pending deletion, decommission start, and Access Policy management events if you want a more detailed administrative activity stream.

Access Policy lifecycle messages confirm that a policy definition changed. They do not mean the policy has been assigned to a service.

## Verify a real event

After the test message succeeds, verify one disposable lifecycle event:

1. Enable **Rule activated**.
2. Start a disposable DockFlare-enabled container or create a disposable manual rule.
3. Wait for its tunnel, DNS, and optional Access work to complete.
4. Confirm Discord receives one activation message with a clickable HTTPS service URL.
5. Remove the disposable resource and confirm DockFlare returns to its previous state.

Do not use a production service solely for notification testing.

## Troubleshooting

### DockFlare rejects the destination

- For a direct Discord destination, confirm you pasted the complete `https://discord.com/api/webhooks/{WEBHOOK_ID}/{WEBHOOK_TOKEN}` URL. The optional `discord://` format is also accepted.
- For an Apprise API destination, confirm the scheme is `apprise://` or `apprises://`.
- Confirm the URL contains no placeholder braces.
- Confirm the webhook ID, token, API host, port, and configuration key are complete.

### Apprise works in the browser but DockFlare cannot reach it

From the DockFlare container, verify that the API hostname resolves and port 8000 is reachable. The browser reaching a host address does not prove that the DockFlare container can reach the same address.

For a shared network, confirm both containers are attached:

```bash
docker network inspect cloudflare-net
```

The container name `apprise` must appear in the network membership before this URL can work:

```text
apprise://apprise:8000/{CONFIG_KEY}
```

### The API returns configuration-not-found or HTTP 404

- Copy the configuration key again from Apprise.
- Confirm the persistent configuration was saved.
- Confirm `./config` is mounted at `/config`.
- Confirm DockFlare is pointing to the correct Apprise API instance.

### Discord receives no message

Test each link in order:

1. Test the Discord destination from Apprise, or test the direct destination in DockFlare.
2. Test the stored Apprise configuration from the Apprise web interface.
3. Test delivery from DockFlare.
4. Trigger a disposable real event.

The first failing step identifies which connection needs attention.

### Discord receives duplicate messages

- Confirm the same Discord webhook is not listed more than once in the stored Apprise configuration.
- Confirm DockFlare does not contain both the direct Discord URL and an Apprise API URL that forwards to the same webhook.
- Check whether separate DockFlare instances are using the same destination.

### A saved DockFlare destination is not visible

DockFlare never displays complete saved destination URLs. A blank replacement field does not mean the destination was removed. Check the redacted destination count and scheme instead.

## Maintain the Apprise API

Back up the deployment's `config` directory before upgrading.

Update the container with:

```bash
docker compose pull
docker compose up -d
```

Verify `/status`, send an Apprise test, and then send a DockFlare test after the upgrade.

## Security checklist

- Keep Discord webhook URLs and Apprise configuration keys secret.
- Restrict access to port 8000 and the Apprise administrative interface.
- Use HTTPS when traffic crosses an untrusted network.
- Protect the persistent `config` directory and its backups.
- Rotate a Discord webhook immediately if its URL is exposed.
- Configure only notification destinations you trust.
- Never include real secrets in screenshots, support requests, or logs.

## Related documentation

- [Notifications with Apprise](Apprise-Notifications.md)
- [Apprise API project](https://github.com/caronc/apprise-api)
- [Apprise Discord service](https://appriseit.com/services/discord/)
- [Discord webhooks](https://support.discord.com/hc/en-us/articles/228383668-Intro-to-Webhooks)
