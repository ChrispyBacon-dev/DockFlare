# Notifications with Apprise

DockFlare can send operational notifications through [Apprise](https://github.com/caronc/apprise), an independent third-party open-source notification framework. Apprise supports Discord, Telegram, Slack, email, generic webhooks, and many other services.

Notifications are optional and disabled by default. Existing DockFlare installations continue to operate normally when no destination is configured. Notification delivery is best-effort and never changes the result of the DockFlare operation that produced the event.

## Choose a setup

Apprise is already bundled inside the DockFlare container. You do not need to install Apprise or run another container to use supported destinations directly. A separately deployed Apprise API is optional.

| Setup | Best for | What you enter in DockFlare |
|---|---|---|
| Direct destination | One or a few services and the simplest setup | A supported provider URL, such as the Discord webhook copied from Discord |
| Self-hosted Apprise API | Central configuration shared by several applications | An API URL such as `apprise://apprise:8000/{CONFIG_KEY}` |

For a complete Discord example covering both options, see [Discord Notifications and Apprise API](Discord-Apprise-Notifications.md).

## Configure DockFlare

1. Open **Settings**.
2. Select **Notifications**.
3. Paste one complete Apprise URL per line into **Replacement Apprise URLs**.
4. Select the events you want to receive.
5. Enable notifications.
6. Select **Save notification settings**.
7. Select **Send test notification** and wait for the delivery result.

The replacement field is intentionally blank whenever the page loads:

- Leaving it blank retains every currently saved destination.
- Entering one or more URLs replaces the complete saved list.
- Selecting **Clear all configured destinations** removes the saved list when the form is saved.
- You must save a new destination before testing it.

Complete destination URLs are never displayed again after saving. The settings page shows only a redacted scheme and destination count.

## Available events

Event controls are grouped by purpose.

### Rule lifecycle

- Rule activated
- Rule restored
- Rule pending deletion
- Rule deleted

### Cloudflare and system failures

- Cloudflare tunnel update failure
- Cloudflare DNS failure
- Cloudflare Access failure
- Docker listener stopped

### Agent lifecycle

- Agent enrolled
- Agent enrollment failed
- Agent offline
- Agent recovered
- Agent decommission started
- Agent decommission completed
- Agent decommission failed
- Agent decommission timed out

### Tunnel health

- Tunnel down
- Tunnel recovered

### Access Policy management

- Access Policy created
- Access Policy updated
- Access Policy deleted

Access Policy lifecycle notifications report administrative changes only. Creating a policy does not assign it to a service. Services must still reference the policy through the UI, API, or Docker labels.

Routine administrative events are opt-in. Recommended failure, recovery, enrollment, and terminal decommission events are enabled by default in a new notification configuration. You can change every event independently.

## Cooldowns and recovery messages

Repeated failure notifications for the same resource are limited by the configured failure cooldown. The default is 900 seconds.

Recovery messages are correlated with incidents:

- `Agent recovered` is sent only when DockFlare previously sent an offline alert for that Agent.
- `Tunnel recovered` is sent only when DockFlare previously sent a down alert for that tunnel.
- The initial healthy observation establishes a baseline and does not send a recovery message.

Normal startup scans are suppressed to avoid replaying historical rule events. Expected Agent and tunnel health changes during decommissioning or an intentional restart are also suppressed.

## Delivery behavior

Notifications are placed on a bounded in-memory queue and delivered by a background worker. A slow or unavailable destination does not block Docker events, Agent processing, Cloudflare operations, reconciliation, or web requests.

Keep these limitations in mind:

- Queued messages can be lost if DockFlare exits before delivery.
- Failed delivery is not automatically retried because some destinations may already have received the message.
- Queue, cooldown, health-baseline, and recent test-job state are cleared by a restart.
- A full queue drops new notification events rather than delaying DockFlare's primary work.

## Security

Treat every Apprise destination URL as a secret. URLs commonly contain webhook tokens, API keys, usernames, passwords, or a stored configuration key.

- DockFlare stores destinations in its encrypted configuration, not in `state.json`.
- Saved URLs are redacted from the UI, API responses, and logs.
- Encrypted backups contain the notification configuration and its encryption key. Protect backups accordingly.
- Configure only destinations and Apprise API servers you trust. A destination can make DockFlare connect to an internal or external address.
- If a Discord webhook or another destination URL is exposed, rotate or delete it at the provider and save the replacement in DockFlare.

## Troubleshooting

| Problem | Check |
|---|---|
| Test button is disabled | Save at least one valid destination and enable notifications first. |
| Destination validation fails | Compare the URL with the [Apprise service documentation](https://appriseit.com/services/). |
| Test remains pending | Check DockFlare logs and confirm the notification worker is running. |
| Delivery fails | Confirm the DockFlare container can resolve and reach the destination host and port. |
| Apprise API works in a browser but not from DockFlare | Do not use `localhost` unless the API runs in the DockFlare container. Use a shared Docker-network service name or a reachable host address. |
| Settings field is blank after reload | This is intentional. Leaving it blank preserves the saved destinations. |
| Discord reports an invalid webhook | Verify both the webhook ID and token, or create a new Discord webhook. |
| Messages repeat during an incident | Increase the failure cooldown and check whether the resource identifier is changing between events. |

DockFlare logs include a secret-free event ID and aggregate delivery result. They do not include complete destination URLs.

## Related documentation

- [Discord Notifications and Apprise API](Discord-Apprise-Notifications.md)
- [Apprise project](https://github.com/caronc/apprise)
- [Apprise notification services](https://appriseit.com/services/)
- [Apprise API project](https://github.com/caronc/apprise-api)
- [Discord webhook documentation](https://support.discord.com/hc/en-us/articles/228383668-Intro-to-Webhooks)
