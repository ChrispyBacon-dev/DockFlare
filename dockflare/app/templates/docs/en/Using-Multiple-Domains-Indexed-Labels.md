# Using Multiple Domains (Indexed Labels)

DockFlare provides a powerful feature called **indexed labels** that allows you to define multiple, independent ingress rules for a single container. This is particularly useful when you want to expose different ports or paths of the same service on different public hostnames.

## How It Works

To create multiple rules, you simply prefix the standard DockFlare labels with an integer and a dot, starting from `0`. For example, `dockflare.0.hostname`, `dockflare.1.hostname`, and so on.

*   Each index (e.g., `0`, `1`, `2`) represents a separate ingress rule.
*   An indexed hostname (e.g., `dockflare.<index>.hostname`) is always required to initiate a new rule.
*   Other labels at the same index (e.g., `dockflare.<index>.service`) will apply only to that specific rule.

## The Fallback Mechanism

A key feature of indexed labels is the fallback mechanism. If you do not provide a specific indexed label for a rule, it will **fall back to the value of the corresponding base (non-indexed) label**.

This allows you to define common settings once at the base level and only override the specific values that need to change for each indexed rule.

## Example: Exposing a Web UI and an API

Let's say you have a single container that serves both a web application on port `80` and a separate API on port `3000`. You want to expose them on `app.example.com` and `api.example.com` respectively. You also want to secure the API with a specific Access Group, while the main app remains public.

Here is how you would configure this using indexed labels:

```yaml
services:
  my-app:
    image: my-application
    restart: unless-stopped
    networks:
      - cloudflare-net
    labels:
      - "dockflare.enable=true"

      # --- Base Labels (Fallback) ---
      # This service is used by rule 0, as it's not specified there.
      - "dockflare.service=http://my-app:80" 

      # --- Rule 0: The Web UI ---
      - "dockflare.0.hostname=app.example.com"
      # No 'service' label here, so it falls back to the base one.
      # No 'access.group' label, so it's public.

      # --- Rule 1: The API ---
      - "dockflare.1.hostname=api.example.com"
      # Override the service to point to the API port.
      - "dockflare.1.service=http://my-app:3000"
      # Add a specific access policy for this rule only.
      - "dockflare.1.access.group=api-users-policy"
```

### Breakdown of the Example

*   **Rule 0 (`app.example.com`)**:
    *   It defines `dockflare.0.hostname`.
    *   It does not define `dockflare.0.service`, so it falls back to the base `dockflare.service` and uses `http://my-app:80`.
    *   It's a public service because no access policy is defined for this index or at the base level.

*   **Rule 1 (`api.example.com`)**:
    *   It defines `dockflare.1.hostname`.
    *   It **overrides** the service with `dockflare.1.service`, pointing to the API port `3000`.
    *   It applies a specific security policy using `dockflare.1.access.group`. This label only affects this rule.

This approach keeps your label configuration clean and avoids repetition, making your `docker-compose.yml` files easier to read and maintain.
