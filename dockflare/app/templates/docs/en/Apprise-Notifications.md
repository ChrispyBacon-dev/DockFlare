# Apprise Notifications

DockFlare can send operational notifications to services supported by [Apprise](https://github.com/caronc/apprise), including chat, push, email, and webhook providers. Notifications are disabled by default and delivery is best-effort; a destination failure never changes the result of the DockFlare operation that produced the event.

## Configure notifications

1. Open **Settings** and select **Notifications**.
2. Paste one complete Apprise URL per line into **Replacement Apprise URLs**.
3. Select the events you want to receive.
4. Enable notifications and save.
5. Select **Send test notification** and wait for the delivery result.

The replacement field is intentionally blank whenever the page loads. Leaving it blank retains the currently saved destinations. Entering URLs replaces the entire list. To remove the saved destinations, select **Clear configured destinations** and save.

Consult the [Apprise service documentation](https://github.com/caronc/apprise/wiki) for provider-specific URL formats. Keep these URLs secret: they commonly contain webhook tokens, API keys, usernames, or passwords.

## Available events

DockFlare can report:

- rule activation, restoration, pending deletion, and completed deletion;
- Cloudflare tunnel configuration, DNS, and Access failures;
- an unexpected Docker listener failure;
- Agent offline and recovery transitions; and
- managed tunnel down and recovery transitions.

Repeated failure notifications for the same resource are limited by the configured cooldown. Recovery notifications are sent only when DockFlare previously emitted the corresponding outage notification. Normal startup scans and intentional Agent or tunnel stops are suppressed to avoid misleading alerts.

## Delivery behavior

Notifications are queued in memory and sent by a background worker, so a slow destination does not block Docker or Cloudflare processing. The queue is bounded; when it is full, new notification events are dropped and counted in the notification status. Queued messages can be lost if DockFlare exits before delivery, and failed deliveries are not automatically retried because some destinations may already have received the message.

The settings page displays only redacted destination summaries. Complete URLs remain in DockFlare's encrypted configuration and are included in encrypted backups, so backups must also be handled as secrets.

## Troubleshooting

- If testing is unavailable, save at least one valid destination and enable notifications first.
- If a test fails, review DockFlare logs for the event ID and aggregate delivery result. Destination URLs are not written to logs.
- Confirm the DockFlare container can resolve DNS and reach the destination over the required outbound port.
- Verify the provider credentials and URL syntax against the Apprise documentation.
- A restart clears queued messages, cooldown state, health baselines, and recent test-job results.
